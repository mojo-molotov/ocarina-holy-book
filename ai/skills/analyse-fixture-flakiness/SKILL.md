---
name: analyse-fixture-flakiness
description:
  '**Hunt flakiness at the setup / teardown boundary** of the Ocarina test suite — the dance that happens *around* each test (driver acquisition from
  the pool, browser warm-up, login fixture, cookie state, base URL navigation, post-test cleanup, driver release back to the pool, screenshot capture
  on failure). Flakes here look different from in-test flakes: a test that fails on its *first action* probably failed in setup; a test that passes
  but leaks state into the next one probably failed in teardown; a worker that wedges between tests is a release-step bug. The skill instruments the
  setup and teardown paths with extra observation (logs, screenshots, state dumps), runs the suite under stress (high replay, `--workers` saturation),
  and surfaces **fixture-localised** chronic failures distinct from in-test deaths. Use whenever the user asks to investigate per-test setup flakes,
  suspect the login fixture, see cross-test contamination, debug a wedged worker, or audit teardown leaks. Distinct from `analyse-flakiness`: that
  widens the transient net inside test bodies; this instruments the boundaries.'
---

# Analyse fixture flakiness — instrument the setup / teardown boundary

A diagnostic skill complementary to `analyse-flakiness`. That skill hunts flakes inside test bodies; **this** skill hunts flakes in the _boundary_
machinery — everything that happens before the first test action and after the last assertion.

The boundary is where the most confusing flakes live, because their symptoms manifest _inside_ the next test (or as a wedged worker, or as a leaked
cookie). Without dedicated instrumentation, those flakes look like in-test bugs and waste an investigation budget.

## The boundary surfaces (where flakes hide)

Eight surfaces, in roughly the order they execute around a test:

### 1. Driver pool acquisition

Ocarina pulls a driver from a pool (`create_drivers_pool.py`). Flake shapes here:

- Pool exhaustion (more concurrent tests than drivers) — symptom: timeout before the first action.
- Stale driver returned (previous test left it in a dirty state) — symptom: first action fails on a page that "shouldn't" exist.
- Driver crashed between tests (Chrome / geckodriver subprocess died) — symptom: first WebDriver call raises `WebDriverException: invalid session id`.

### 2. Browser warm-up

The driver is open but the browser hasn't navigated yet:

- Cold profile vs warm profile (clean Chrome with password-manager off vs profile-reuse).
- Heroku dyno cold-start (the _server_ not warm — surfaces as a slow first GET).

### 3. Login fixture / authentication state

The test arrives expecting `DEMO_USERNAME` to be logged in (or expecting _not_ to be):

- Previous test logged out cleanly? Or left a session cookie?
- The login dance itself flaked (the `§A-ENV-2` password-modal symptom is exactly this).
- A redirect didn't complete — the test "is logged in" but lands on the wrong page.

### 4. Base URL / starting page

The test assumes the browser is at `LOGIN_URL` / `HOME_URL` / wherever. Flake shape:

- Previous test left the browser elsewhere; setup forgot to navigate.
- The fixture navigated but Chrome's BFcache served a stale snapshot (the §B-BROWSER-1 shape).

### 5. Test body executes — out of scope here, see `analyse-flakiness`.

### 6. Teardown — post-action cleanup

- Did logout actually fire?
- Did the test leave a created appointment in the demo account? (CURA's demo backend is shared — leaked appointments contaminate `REQ-HIST-*` tests.)
- Did the test set cookies that the next test will mis-interpret?
- Did the screenshot-on-failure step itself fail silently and lose evidence?

### 7. Driver release back to the pool

- Did the driver close cleanly? Or is it returned in a half-broken state?
- Did the worker correctly mark the slot free?
- Did the driver leak processes (orphan chromedriver / geckodriver)?

### 8. Worker idle → next acquisition

Between two tests on the same worker, what's the state? An "empty" gap is the easiest place for a bug to hide — there's no test running, so there's no
log line to surface it.

## The mechanism

Two motions, used together:

- **Instrumentation** — add log calls at the boundary (entry/exit of each setup step, entry/exit of each teardown step, plus a state dump:
  `driver.current_url`, `driver.get_cookies()`, `driver.title`). Temporary. Removed at the end.
- **Stress** — run the suite under conditions that **amplify** boundary flakes: high replay count, `--workers` saturation (more workers than tests
  cleanly), back-to-back rapid runs (no dyno cool-down).

With both in place, the logs let you draw a timeline per worker: _driver picked up → warm-up done → login → test ran → teardown started → driver
returned_. Gaps, repeats, or wrong-order entries are the flakes.

## Procedure

### Step 1 — Restate the hypothesis

"A wedged worker has been killing the Chrome runs about once per CI day." Or "After §A-ENV-2 was supposedly resolved, I still see the
first-action-fails pattern occasionally — is the login fixture really clean?" Or "Audit all boundary surfaces — I don't have a specific suspect."

A narrow hypothesis aims at one or two surfaces. A broad audit covers all eight.

### Step 2 — Locate the boundary machinery

```bash
grep -rn "create_drivers_pool\|setup\|teardown\|fixture" src
grep -rn "before_each\|after_each\|before_all" src
```

Ocarina's exact primitives may differ (read the framework's docs at `<gitignored>/ocarina/` if needed). Identify:

- Where the driver is acquired and released.
- Where pre-test login happens (a scenario-level fixture? a campaign-level one?).
- Where post-test cleanup happens (logout? cookie clear? navigate-home?).
- Where screenshots-on-failure are captured.

Make a note of every file you'd need to instrument.

### Step 3 — Surface the experiment plan

```markdown
# Fixture-flakiness analysis plan

## Hypothesis

<one-sentence>

## Surfaces under scrutiny

- <pool acquisition | warm-up | login | base URL | teardown | release | idle gap> — <why suspect>.

## Instrumentation (temporary, will be reverted)

- `src/<file>.py:<line>` — add log call at <entry|exit> of <step>. Captures: <`current_url`, `cookies`, `title`, timestamp, worker id>.
- ... (one bullet per insertion)

## Stress shape

- Replays: <N, default 5>.
- Workers: <as configured | bumped to amplify contention>.
- Browsers: <chrome | firefox | both>.
- Back-to-back: <one run after another with no pause | spaced>.

## Output capture

- Logs root per `pick-logs` (mtime, not name).
- Reports per `pick-reports`.
- Screenshots per `pick-screenshots`.

## Restore

- Revert all instrumentation at the end. Do not commit.
```

Wait for the user's go. Instrumentation is authoring data — the user signs off per "Datasets are authoring decisions".

### Step 4 — Instrument

Add log calls at the agreed surfaces. Standard shape:

```python
logger.info(
    "fixture_boundary",
    extra={
        "step": "<acquire_driver|warm_up|login|base_url_nav|teardown_logout|release|...>",
        "phase": "<enter|exit>",
        "worker_id": <id>,
        "current_url": driver.current_url if driver else None,
        "cookie_count": len(driver.get_cookies()) if driver else 0,
        "title": driver.title if driver else None,
    },
)
```

Don't dump full cookie contents (credentials / session tokens may be present). Dump counts and names; the empirical question is "did the cookie
exist?", not "what's inside".

Run `ruff format && ruff check && mypy` after the insertions — broken instrumentation that fails CI is worse than no instrumentation.

### Step 5 — Run under stress

Drive the run shape from Step 3. After each replay:

- Capture the latest log root (mtime).
- Capture the JSON report.
- Snapshot any failure screenshots (mtime-sorted).

Don't mix replays in your head. Each one is its own observation.

### Step 6 — Reconstruct the per-worker timeline

For each worker, across all replays, build the sequence:

```
worker 1, replay 1:
  T+0.00s  acquire_driver  enter
  T+0.42s  acquire_driver  exit          (clean)
  T+0.43s  login           enter         url=/profile.php#login cookies=0
  T+2.18s  login           exit          url=/ cookies=1 (PHPSESSID)
  T+2.20s  test_A          (starts)
  T+12.4s  test_A          (passed)
  T+12.4s  teardown        enter         url=/history.php cookies=1
  T+13.1s  teardown        exit          url=/ cookies=0
  T+13.1s  release         enter
  T+13.2s  release         exit          (clean)
  ...
  T+15.0s  acquire_driver  enter
  T+15.0s  acquire_driver  exit          (clean)
  T+15.1s  login           enter         url=/ cookies=0     <- previous teardown was clean
  T+17.5s  login           exit          url=/ cookies=1
  ...
```

Then look for:

- **Long gaps** between teardown-exit and next acquire-enter — worker stalled.
- **Non-zero cookie count** at login-enter on a fresh acquisition — previous teardown leaked.
- **Wrong URL** at login-enter — previous teardown left the browser elsewhere (BFcache restore? Stuck on a half-redirected page?).
- **Missing exit** for any phase — the worker died mid-fixture; the next test is going to start on a corrupt driver.
- **Repeated enter without exit** — a phase entered, didn't finish, was retried, and the original is dangling.

### Step 7 — Classify the findings

For each anomaly:

- **Chronic** — same anomaly across ≥ 2 replays. Real boundary flake.
- **One-off** — single replay. Probably noise, but record for a future pass.
- **Cross-references** — does the anomaly match `§A-ENV-1` (rapid-POST contention), `§A-ENV-2` (password modal), `§B-BROWSER-1` (BFcache), or none?

### Step 8 — Surface the findings

```markdown
# Fixture-flakiness analysis — <one-sentence hypothesis>

## Experiment

- Surfaces instrumented: <list>.
- Run shape: <browsers>, <N> replays, workers <count>.

## Chronic boundary anomalies

| Worker / replay | Surface         | Anomaly                                                   | Symptom in test                                             | Cross-ref                                                          |
| --------------- | --------------- | --------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------ |
| w2 / r1,r3      | teardown_logout | exit without redirect; cookies still set                  | next test (test_B) failed at first action with "wrong page" | §B-BROWSER-1 (BFcache stale page)                                  |
| w1 / r2,r3      | release         | enter then 8s gap before next acquire                     | worker appeared wedged in CI summary                        | none — new finding                                                 |
| w3 / r1,r2,r3   | login           | password modal symptom (selector miss on `#txt-password`) | first action timed out                                      | §A-ENV-2 (clean Chrome should fix; was it applied to this driver?) |

## One-offs (recorded, not actionable)

- <…>

## Cross-references

- `IDENTIFIED_GAPS.md` §<refs>.
- `src/<fixture file>.py:<line>` — site of the anomaly.

## Open follow-ups

- Per-anomaly: <isolate via `write-a-probe` | file as new gap | fix in the fixture code | re-run with tighter scope>.

## Verdict

<one-line: N chronic boundary flakes, K resolved by cross-ref, nothing material, …>.
```

### Step 9 — Restore the instrumentation

```bash
git diff -- src
git checkout -- <each instrumented file>
```

Confirm the restore with a second `git diff`. Boundary instrumentation is throwaway; the _findings_ land elsewhere (a comment on the fixture, an entry
in `IDENTIFIED_GAPS.md`, a deliberate refactor of the fixture).

If the analysis surfaced a permanent log call worth keeping (rare — production-grade fixture observability), that's a separate signed-off change, not
"leave the diff in".

### Step 10 — Stop. The user decides.

Each chronic anomaly can resolve as:

- **Fix in the fixture** — the teardown forgot to clear cookies; add it. The acquisition forgot to verify a clean driver; add a check.
- **File as gap** — the anomaly is environmental and not fixable in the suite (`A-ENV-*`).
- **Probe further** — invoke `write-a-probe` to isolate the root cause of a wedged worker.
- **Defer** — interesting but rare.

## Hard rules

- **Never commit the instrumentation.** It's a probe of the boundary. The restore is mandatory.
- **Don't dump cookie / credential contents into logs.** Counts and names only. The demo creds are public, but anything _issued by the server_
  (session tokens) shouldn't land in a log file you might paste into a PR.
- **Stress is amplification, not abuse.** Bumping workers to amplify contention is fine. Hammering the Heroku dyno with thousands of requests is not —
  it's a free-tier deployment.
- **Multiple replays are mandatory.** A single replay's gap could be a CI hiccup. Default 5 here (one more than the in-test analysis), because
  boundary flakes are rarer per-test than in-test ones.
- **Distinguish from `analyse-flakiness`.** If a "boundary" symptom turns out to be the _test body's_ first action genuinely failing (e.g. a selector
  drift), hand off to `analyse-flakiness` or `write-a-probe`. The two skills cover adjacent territory.

## When to run this skill

- A worker wedges in CI without an obvious cause.
- First-action timeouts cluster on specific tests but the test bodies look fine.
- A test passes in isolation but fails when run after a specific other test (cross-test contamination → almost always a teardown leak).
- After a fixture refactor — verify the boundary still behaves.
- The `§A-ENV-2` symptom returns despite the clean-Chrome adapter — is the adapter actually being applied to every acquisition?

## What this skill does NOT do

- It does not run automatically. The user signs off on the instrumentation plan.
- It does not leave instrumentation behind. Restore is non-optional.
- It does not fix the fixture code as part of the analysis. Fixes are a follow-up motion (often via `update-frd-and-tests` or a direct edit signed off
  by the user).
- It does not investigate in-test flakes — that's `analyse-flakiness`.
- It does not run probes (`write-a-probe`) — it surfaces the anomalies; probes are a follow-up motion.
- It does not include attack-shape inputs anywhere. Per `CLAUDE.md` → "Security testing is functional and static — never active".
