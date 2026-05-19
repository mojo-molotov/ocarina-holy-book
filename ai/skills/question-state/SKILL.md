---
name: question-state
description:
  Diagnostic checklist for when a test or run behaves unexpectedly — **question the environment state before blaming the SUT or the code**. Walks the
  load-bearing state surfaces of the run environment (hosting-platform warm/cold, account/session persistence, leftover `.reports/` /
  `.ocarina_logs_*` / `.webdriver_profile_*` artifacts, browser-profile cleanliness, `--workers 3` concurrent access to a shared demo account,
  deployed-SUT vs source drift, chromedriver/geckodriver/browser version skew, recent driver or browser updates) and surfaces what to verify first.
  The environment is often "bouchonné" — half-configured, half-cached, half-warm — and a noisy failure that gets blamed on the test code is frequently
  a state artifact. Use whenever the user asks why a test misbehaves, why one run differs from another, why a flake appeared, why a fresh dispatch
  surprises, or before reaching for "the SUT must have changed". Cross-references the project's gap inventory for catalogued environmental artifacts.
---

# Question the environment state before blaming the SUT

A diagnostic skill. When a test or a run behaves in a way that surprises you, **stop and question the state of the environment** before asserting "the
SUT changed" or "the test is broken". This suite typically runs against a live deployment (e.g. a Heroku eco dyno), with a _shared_ demo account, with
browser profiles created on the fly, with reports / logs / screenshots accumulating on disk — and any one of those layers can be in a state that's
quietly biasing the outcome.

The skill is a checklist of state surfaces, each with how to verify it and how to neutralise it. The audit never "fixes" silently — it surfaces what's
suspect and lets the user decide.

This is the empirical companion to `empiricism` and `write-a-probe`: those tools answer _what does the SUT do?_; this one answers _what state is the
run in?_. Run it first when symptoms don't match the documented expected categories.

## The state surfaces (the load-bearing checklist)

For every diagnostic, walk these in order — cheapest first.

### 1. Heroku dyno warm / cold

CURA runs on a Heroku eco dyno that sleeps after inactivity. A cold dyno makes the first request slow; a `--workers 3` run can hit a half-warm dyno
and one worker gets a slow start. Cold-start cascades into false `TimeoutException`s (which auto-retry per `transient_errors`) and into surprise
greens on gap tests (the silent 2nd-POST drop, §A-ENV-1). Same shape on any SUT hosted on a sleep-after-inactivity tier (Fly.io free, Vercel Hobby,
etc.).

Verification:

```bash
# is the instance awake right now?
curl -sf --max-time 30 https://<sut-url>/ -o /dev/null && echo "awake" || echo "cold or down"

# warm it explicitly before a local run
curl -sf --retry 6 --retry-delay 5 --retry-all-errors --max-time 30 https://<sut-url>/ > /dev/null
```

A mature CI workflow usually does this as a "Warm up hosting" step before the run. Local runs don't — flag if the local run was the first hit after a
long pause.

### 2. Demo account history persistence

CURA's `$_SESSION['history']` is server-side, scoped to PHP session. **A logged-in user's history outlives one Python test process** for as long as
the `PHPSESSID` cookie is valid. Across `--workers 3`, three browser workers can simultaneously log in as `John Doe` — and they share the demo
account's recent history if the server stores it per username rather than per session (CURA stores per session, but session lifecycle is what to
question). Same principle applies to any session-cookie-based SUT (JWT in a cookie, opaque session ID, etc.).

Verification: log in via a one-shot probe, navigate to `/history.php`, inspect what's there before the run started:

```python
# <gitignored>/probe_demo_history.py — see `write-a-probe` skill
# log in → driver.get(HISTORY_URL) → print driver.page_source[:2000]
```

If the history is non-empty for tests that assume empty, that's the cause. `rapid_logout_relogin` and `empty_history` in `ocarina-with-ai-example`
both rely on a fresh-login history being empty — CURA's `_f::logout()` does `session_unset()` + `session_destroy()` (documented in the gap inventory),
so a _new_ login starts fresh. But state from a still-live cookie is a different story.

### 3. Leftover local artifacts

Each run writes to `.reports/`, `.ocarina_logs_*`, `.screenshots/`, and creates a `.webdriver_profile_*/` temp dir per chrome driver. Accumulation:

- **`.reports/json/*.json`** — every prior run's JSON results pile up. The most-recent one is the one to read
  (`ls -t .reports/json/*.json | head -1`).
- **`.reports/docx/<run-id>/`** — same, plus the DOCX proofs.
- **`.ocarina_logs_*/`** — one directory per run.
- **`.webdriver_profile_*/`** — chrome temp profiles. `DriverBuilder` should clean these on `dispose()`, but force-killed runs leave them.

Verification:

```bash
ls -dt .reports/json/* .reports/docx/* .ocarina_logs_* .webdriver_profile_* 2>/dev/null | head -10
du -sh .reports .ocarina_logs_* .webdriver_profile_* 2>/dev/null
```

The runtime CLI flag `--dont-force-delete-tmp-dirs` controls automatic cleanup on Windows (per Ocarina's `create_cli_store.py`). Leftover artifacts
don't usually cause test failures, but they cause **the audit-of-the-audit problem** — you read a JSON from the wrong run and reach the wrong
conclusion. Always pin which run's JSON you're reading.

### 4. Browser profile cleanliness

Chrome should run with the consumer password manager off (e.g. via the project's `create_drivers_pool.py`). If a probe or a local invocation bypasses
the adapter and launches plain Chrome, the post-login breach modal is back and _every_ downstream action looks like the test framework hanging. The
known environmental finding documented in the gap inventory should call out the resolution; the artifact returns the moment the adapter isn't used.

Verification: which path produced this run's chrome? If the user ran `python src/main.py` then it went through the adapter — good. If a one-off probe
was launched, did it mirror the adapter's options? (The `write-a-probe` skill says it must.)

### 5. `--workers 3` concurrent access to the demo account

Three browsers logging in as `John Doe` at the same time. CURA's `_f::login()` compares with `===` and has no rate limit / lockout (per the gap
inventory's security section). So three simultaneous logins are _fine_ on CURA's side — but on the Heroku eco dyno, three simultaneous POSTs can
produce the `--workers 3` shared-dyno rapid-POST flake (§A-ENV-1). Same shape on any SUT with a tight hosting tier.

Verification: was the symptom a `TimeoutException` on a second-in-a-row POST? Did the test that flaked do a rapid second submission (saturation,
history ordering's second booking)? If yes, §A-ENV-1 is the explanation — not a regression.

### 6. Deployed SUT vs source drift

`https://katalon-demo-cura.herokuapp.com/` is what the suite tests. `https://github.com/katalon-studio/katalon-demo-cura` is the source. They can
drift. CSRF is the canonical CURA example (documented in the gap inventory): the GitHub source calls `$antiCSRF->insertHiddenToken()` before the
appointment form's submit; the deployed app does **not** render the hidden input. Reasoning from the source on assertions about the deployed app is
exactly the misdiagnosis trap. Same principle applies to any open-source SUT — verify against the live deployment.

Verification: read the rendered HTML of the deployed page, not the source:

```bash
curl -s 'https://katalon-demo-cura.herokuapp.com/profile.php' | grep -i csrf
```

When source-reading is load-bearing (per `CLAUDE.md` → "Verify SUT behaviour"), confirm against the live deployment too.

### 7. Driver / browser version skew

`chromedriver` must match the installed Chrome major version; `geckodriver` is more forgiving but still has bounds. The CI workflow installs a fresh
chromedriver matched to the runner's `google-chrome-stable`. Locally, a stale chromedriver against an auto-updated Chrome is a classic source of
"tests pass on CI, fail locally" or vice-versa.

Verification:

```bash
google-chrome --version 2>/dev/null || google-chrome-stable --version 2>/dev/null
$(<chromedriver-path>) --version
```

If majors don't match, that's a strong suspect.

### 8. Recently-updated browser or driver

Chrome auto-updates; Firefox auto-updates. A symptom that began _today_ and the browser updated _yesterday_ is a strong correlation. Check the system
update history:

```bash
# macOS
ls -lt "/Applications/Google Chrome.app" 2>/dev/null | head -1
# or the system log; method varies per OS
```

If a browser update lines up with the symptom appearing, run a probe with the _previous_ driver version (kept in a separate path) to confirm.

### 9. Time-bound contention

The Heroku eco dyno is shared globally — anyone hitting CURA at the same time uses the same dyno. If a flake appeared _only_ during a specific window
(e.g. a popular Katalon tutorial drives CURA and a class is following along), the dyno may be under unusual concurrent load that has nothing to do
with this suite. Same shape for any shared-tenancy hosting tier.

Verification: easier to reproduce later or in a quiet window. If reproduction is intermittent and only at certain times, this is a candidate cause.

## Procedure

### 1. State the symptom

One sentence. "Two of three Chrome replays of `Journey - History ordered most-recent date first` _passed_ — surprise greens." Or
"`Logout - Session Cleared (via sidebar link)` fails on a fresh local run but passes in CI."

Don't generalise — name the failing test, the browser, the run.

### 2. Walk the checklist top-to-bottom

For each surface, answer the verification question. Mark each:

- **Confirmed cause** — this state explains the symptom.
- **Possible cause** — could contribute; worth ruling out.
- **Not the cause** — verified clean / irrelevant.

Stop walking after a **Confirmed cause** unless the symptom isn't fully explained.

### 3. Cross-reference the catalogued environmental artifacts in the gap inventory

Two catalogued environmental artifacts in `ocarina-with-ai-example`:

- **§A-ENV-1 — `--workers 3` shared-dyno rapid-POST drop.** Symptom: a rapid 2nd-in-a-row POST against CURA on its Heroku eco dyno gets no
  confirmation, `TimeoutException` surfaces after auto-retry. Affects `Saturation`, `Journey - History ordered`, can false-negative the
  duplicate/overlapping gap tests.
- **§A-ENV-2 — Chrome password-breach modal (resolved).** Symptom: any post-login interaction silently does nothing. The driver adapter
  (`create_drivers_pool.py`) disables the consumer password manager so this is no longer hit through `python src/main.py` — but a probe that bypasses
  the adapter can resurrect it.

If the symptom matches a catalogued artifact, that's the explanation.

### 4. Report

Use this exact template:

```markdown
# State-questioning audit — <symptom>

## Walked surfaces

| Surface                         | Status                       | Evidence   |
| ------------------------------- | ---------------------------- | ---------- |
| Hosting warm/cold               | <Confirmed / Possible / Not> | <one line> |
| Account/session persistence     | …                            | …          |
| Leftover local artifacts        | …                            | …          |
| Browser profile cleanliness     | …                            | …          |
| `--workers N` rapid POSTs       | …                            | …          |
| Deployed SUT vs source drift    | …                            | …          |
| Driver / browser version skew   | …                            | …          |
| Recently-updated browser/driver | …                            | …          |
| Time-bound contention           | …                            | …          |

## Catalogued artifacts hit

- <gap-inventory entry ID if any matches>

## Conclusion

<one of:>
- **State explains the symptom.** Cause: <surface>. Remedy: <warm the dyno / clean the profile / pin driver versions / retry in a quiet window>. Do **not** edit tests or POMs to "fix" this.
- **State is clean — the symptom is not environmental.** Hand off to: `empiricism` (verify SUT behaviour), `write-a-probe` (capture concrete state), `review-suite-stability` (run replays).
- **Inconclusive — need a probe.** Specify: <which surface to probe deeper, with what>.

## Next step (if any)

- <one concrete next move>
```

Print the report. Do not edit tests, POMs, drivers, or workflow files. The audit's job is to point at the right next move; the user picks.

### 5. Stop. The user decides.

State diagnoses are _cheap to fix correctly_ (warm the dyno, clean a directory, pin a driver) and _catastrophic to misdiagnose_ (rewriting a test to
compensate for a stale chromedriver is exactly the kind of patch the rest of the skill suite exists to prevent). Hand the report over.

## What this skill does NOT do

- It does not edit tests, POMs, or the suite. Environmental remedies are environmental — warm the dyno, clean the temp dirs, pin the driver — not
  "make the test more tolerant".
- It does not run probes itself — it points at which one (see `write-a-probe`).
- It does not generalise environment artifacts that aren't catalogued. If you find a new one (a third browser-side oddity, a new dyno behaviour), file
  it in the gap inventory's environmental section first, then this audit references it on the next walk.
- It does not silence flakes. A confirmed `--workers 3` shared-dyno flake (§A-ENV-1) is handled by `transient_errors` retry already; if it survives
  the retry, it's a documented artifact, not a regression.

## When to run this skill

- The user asks: "why is this failing?", "why did one run differ?", "is this a flake?", "the test passed yesterday, what changed?"
- A `review-suite-stability` run surfaces a flake, a surprise green, or a surprise red.
- Before reaching for `empiricism` — environmental state is cheaper to rule out than a SUT misdiagnosis.
- After a Chrome / Firefox / driver update on the local machine, if anything starts to misbehave.
- Before invoking `update-frd-and-tests` to "mark a gap resolved" — the surprise green may be an environmental contention finding, not the SUT.
