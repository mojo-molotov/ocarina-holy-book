# CURA Test Suite — Claude Context

Orientation for Claude (and any contributor) working in this repo: where to look, how to work, and what not to do. Keep this file tight.

## Key documents

- [`README.md`](README.md) — human-facing entry point.
- [`CURA_FRD.md`](CURA_FRD.md) — reconstructed functional requirements (pages, IDs, URLs, business rules, §9 known bugs). Read it before writing or
  changing tests.
- [`CURA_TEST_STRATEGY.md`](CURA_TEST_STRATEGY.md) — strategy, taxonomy, expected pass/fail categories. Keep coverage tables, the suite/campaign tree,
  and §7 in sync with the code.
- [`IDENTIFIED_GAPS.md`](IDENTIFIED_GAPS.md) — source-cited CURA defect inventory. Add an entry when you find a new gap; remove it when CURA fixes it.
- [`CLAUDE.local.md`](CLAUDE.local.md) — gitignored, machine-specific (driver paths, ocarina clones). Template below.

## Project

Selenium E2E suite for [CURA Healthcare](https://katalon-demo-cura.herokuapp.com/), built on the **Ocarina** framework (Railway-Oriented-Programming
test runner). Python 3.14+. Demo credentials `John Doe` / `ThisIsNotAPassword` are public and hardcoded in every scenario.

## Project philosophy

The project pushes towards strictness in every dimension: `ruff select = ["ALL"]`, strict `mypy`, `--workers 3`, multi-browser CI matrix. That
pressure exists to make the better solution visible — and to make the hacky shortcut uncomfortable.

- **No tricks or hacks.** JS-clicks to skip hit-testing, `# noqa` to silence a rule, `time.sleep` to mask a race, `driver.implicitly_wait` to patch a
  timing bug. If a hack is genuinely the only option, document why no clean fix exists and mark it so a reader doesn't copy the pattern. The
  JS-click-for-logout incident is the canonical anti-example: `ElementClickInterceptedException` had a clean polling fix; the JS click hid the
  problem.
- **Teach the pattern, not the symptom.** A rule must read as reusable knowledge — _the behaviour to handle correctly_ — not a log of which browser,
  version, library, or POM showed the problem first. Symptom-bound names expire silently the moment they drift. Use concrete examples freely, but keep
  symptom names out of the rule statement itself; they belong in the call-site comment or in `IDENTIFIED_GAPS.md`.

## CLAUDE.local.md template

`CLAUDE.local.md` is gitignored and stores per-machine paths. If it's missing, create it with the template below — and ask for the paths, don't guess.
`find ~/ -name chromedriver -type f 2>/dev/null` locates chromedriver; ocarina clones have no predictable location.

```markdown
# Local machine config

## chromedriver

Path: `/path/to/chromedriver`

## Ocarina source repos (git clones)

- **ocarina**: `/path/to/ocarina`
- **ocarina-example**: `/path/to/ocarina-example`
```

## Layout

**Keep this section in sync with the actual tree.** Any commit that adds, removes, renames, or moves a file under `src/` (or a top-level doc) updates
the block below in the same commit. A stale map misroutes confident readers. Audit:

```bash
python3 -c "
import re, pathlib
tree = {p.name for p in pathlib.Path('src').rglob('*.py') if p.name != '__init__.py'}
listed = set(re.findall(r'\b[a-z0-9_]+\.py', pathlib.Path('CLAUDE.md').read_text()))
missing = tree - listed
print('missing from CLAUDE.md:', sorted(missing) if missing else '(none)')
"
```

Every `src/**.py` (excluding `__init__.py`) appears below. Top-level docs (`README.md`, `CLAUDE.md`, `CURA_FRD.md`, `CURA_TEST_STRATEGY.md`,
`IDENTIFIED_GAPS.md`, `CLAUDE.local.md`) too.

```
README.md                              # human-facing entry point (what it is, setup, running, reports)
CLAUDE.md                              # this file (rules + conventions)
CLAUDE.local.md                        # gitignored — machine-specific paths (create if missing)
CURA_FRD.md                            # functional requirements — read before writing tests
CURA_TEST_STRATEGY.md                  # test strategy, taxonomy, expected pass/fail counts
IDENTIFIED_GAPS.md                     # technical inventory of CURA gaps (source-cited)
src/
  main.py                              # entrypoint — run `python src/main.py`
  pages/                               # Page Object Models (POMBase + SeleniumTitleMixin)
    login.py
    appointment.py
    confirmation.py
    history.py
    home.py
    profile.py
    components/                         # shared UI components — not pages (see "Shared UI components" rule)
      sidebar.py                       # site-wide sidebar nav (logout lives here)
  lib/
    dates.py                           # date helpers (in_days, ...)
    errors.py                          # custom exceptions (BackForwardCacheExposureError)
    connectors/test_steps/             # thin action wrappers (closure pattern)
      login.py
      appointment.py
      confirmation.py
      history.py
      home.py
      profile.py
      sidebar.py                       # connectors for the sidebar component
    ext/ocarina/adapters/
      agnostic/act.py                  # railway act() wrapper
      selenium/
        browser_navigation.py          # SeleniumBackAndForwardNavigationMixin (shared back/forward)
        cli_getters.py                 # reads SeleniumCliStoreSingleton
        create_drivers_pool.py         # drivers-pool adapter — chrome with password manager off
        logs.py                        # log + screenshot handler factories
        test_suite.py                  # TestSuite adapter (autoscreen_on_fail=True)
        test_campaign.py               # TestCampaign adapter
  constants/
    urls.py                            # CURA_URL + per-page full URLs
    credentials.py                     # DEMO_USERNAME / DEMO_PASSWORD (public demo creds)
    transient_errors.py                # (WebDriverException,) — triggers auto-retry
  tests/
    scenarios/                         # one scenario per file; data-driven families are the only exception
      _fragments/auth.py               # reusable pre/post fragments (e.g. login_as_demo_user)
      login/
        valid_login.py
        failed_logins.py               # data-driven: invalid / empty / wrong-case credentials
        logout.py
        post_logout_access.py
        post_logout_bfcache_exposure.py
        post_logout_frenetic_navigation.py
        post_logout_server_invalidation.py
        rapid_logout_relogin.py
        unauthenticated_appointment_access.py
        unauthenticated_history_access.py
        unauthenticated_profile_access.py
      appointment/
        book_appointments.py           # data-driven: Hongkong / Tokyo+readmission / Seoul
        datasets/booking_cases.py      # parameter matrix (BookingCase tuples)
        missing_visit_date_validation.py
        server_side_date_bypass.py
        past_date_booking.py
        enter_on_visit_date_no_submit.py
        duplicate_booking.py
        overlapping_appointments.py
        saturation_booking.py
      history/
        view_history.py
        empty_history.py
      journey/
        book_and_verify_history.py
        history_ordering.py
        sidebar_navigation.py
        sidebar_login_navigation.py
      profile/
        view_profile.py
    suites/
      authentication/
        baseline.py                    # Suite "Authentication baseline" — smoke gate
        session_management.py          # Suite "Session management"
        failure_modes.py               # Suite "Failure modes"
      appointments/
        booking.py                     # Suite "Booking"
        history.py                     # Suite "History"
      profile.py                       # Suite "Profile access"
      user_journeys.py                 # Suite "Cross-feature flows"
    campaigns/
      prerequisites.py                 # Smoke campaign — TestCycle.smoke_tests_campaigns
      authentication.py
      appointments.py
      profile.py
      user_journeys.py
    cycles/
      e2e.py                           # defines E2E_CYCLE_NAME = "CURA E2E"
```

## Ocarina hierarchy

`Test → TestSuite → TestCampaign → TestCycle`. `TestCycle` accepts `smoke_tests_campaigns=` (gate, fail-fast) and `campaigns=` (main); smoke runs
first and gates main.

A **scenario** builds a `list[drive_page(...)]`. Each `drive_page` chains `act()` calls with `.failure()` / `.success()` handlers from `logs.py` —
never inline lambdas.

## Test strategy

The cycle is `cycles/e2e.py` (`E2E_CYCLE_NAME = "CURA E2E"`).

**Smoke (gate, fail-fast):** `Prerequisites` campaign → `Authentication baseline` suite → `valid_login`. If the demo user can't log in, the rest is
uninformative.

**Main (runs only if smoke passes):**

1. `Authentication` — `Session management` + `Failure modes`.
2. `Appointments` — `Booking` (data-driven) + `History`.
3. `Profile` — `Profile access`.
4. `User journeys` — `Cross-feature flows`.

Rules:

- **"Smoke" is structural, not lexical.** Express the gate via `TestCycle.smoke_tests_campaigns=`; never put "smoke" in a name string.
- **Smoke is the minimum that proves the system is alive.** A test belongs in smoke iff its failure makes the rest of the cycle uninformative.
  `valid_login` qualifies; nothing else here does.
- **Each main campaign is feature-shaped, not method-shaped.** Group by _what_ is being exercised; let each campaign expose `happy_paths` /
  `failure_modes` / `baseline` suites as needed.
- **Default mode is fail-fast.** Use `mode="wait-for-all-smoke-tests"` only if you genuinely need both smoke campaigns to attempt regardless of the
  first failing.

### Test duplication with `--workers`

With `--workers N`, Ocarina duplicates single-test suites up to N times to flush concurrency hazards (race conditions, session cleanup, driver reuse).
The `[COPY N]` annotations are not noise — they confirm the saturation framework is active. Expect them on small smoke suites; this is a feature.

### Worker count — leave RAM headroom, scale horizontally

A worker is a full browser process; the suite's RAM ceiling is `peak_per_worker × N`, not `average × N`. Pages are not uniform — a heavier scenario
(long history list, datepicker overlay, post-submit confirmation rendered alongside the form) spikes well above the average. Size workers against the
**peak**, not the average. If the host has no headroom, the first scenario to spike pushes the others into swap, every wait then races GC instead of
the network, and a green suite turns into cascading `TimeoutException`s with no real defect behind them. The failure mode is indistinguishable from a
flaky test, which is the worst kind — it sends you tuning waits when the problem is memory.

Rules:

- **Size against peak-per-worker with a comfort margin** — target steady-state usage well below the host's available RAM (rule of thumb: leave ≥ 25 %
  free at peak). "It fit last time" is not a margin; one heavier page added later eats the slack silently.
- **Prefer horizontal scaling over vertical saturation.** Two hosts at `--workers 3` each, comfortably under their RAM ceiling, beat one host at
  `--workers 6` riding the limit. Two relaxed machines fail independently and informatively; one saturated machine fails _everything_ at once for a
  reason that has nothing to do with the SUT.
- **CI is the reference, not the maximum.** `ai_proof_e2e.yml` runs `--workers 3` on GitHub-hosted runners sized for it. Don't raise local workers
  past CI to "go faster" on a beefier laptop — you diverge from the canonical reference (see "Never `--workers 1`") and trade margin for noise.
- **Diagnose suspected RAM-pressure failures _before_ tuning waits.** Symptoms: timeouts that cluster across unrelated tests in the same run, get
  worse late in the cycle, and disappear at lower `--workers`. Check host memory (`vm_stat` / `Activity Monitor` / `htop`) during a run; if swap is
  active, lower N or scale out — don't lengthen `--wait-timeout`.

## Running tests

```bash
python -u src/main.py \
  --driver-path <path/to/chromedriver> \
  --browser chrome \
  --workers 3 \
  --wait-timeout 10 \
  --logger terminal+file
```

- **Never `--workers 1`.** Single-worker runs mask concurrency failures and diverge from CI. Always `--workers 3` (matches `ai_proof_e2e.yml`); CI is
  the canonical reference.
- **`src/` is a source directory, not a Python package.** No `src/__init__.py`; nothing is imported as `src.X`. Running `python src/main.py` puts
  `src/` on `sys.path[0]`, so bare `from constants.urls import …` / `from pages.login import …` resolve. CI runs the script form.

CLI flags (all optional with defaults):

| Flag                             | Purpose                                                           |
| -------------------------------- | ----------------------------------------------------------------- |
| `--browser`                      | `chrome` / `firefox` always; `edge` on Windows; `safari` on macOS |
| `--driver-path`                  | Path to the matching driver binary                                |
| `--profile-path`                 | Browser profile directory to start from                           |
| `--not-headless`                 | Show the browser UI                                               |
| `--workers N`                    | Parallelism (always `3`)                                          |
| `--wait-timeout`                 | Per-operation wait, seconds                                       |
| `--only ID …` / `--exclude ID …` | Filter tests by id                                                |
| `--logger`                       | `mute` / `terminal` / `file` / `terminal+file`                    |

Use `--logger terminal+file` when reports must be generated (the DOCX generator reads the log tree).

## Reports and screenshots

Every run writes into `.reports/` (gitignored):

- **DOCX proofs** — `.reports/docx/<run-id>/` — one document per test, embedding a screenshot at every page transition.
- **JSON results** — `.reports/json/<uuid>.json` — machine-readable pass/fail.

Both come from `run_plugins` in `main.py` via `generate_docx_proof` and `generate_json_results`. The DOCX generator reads the log tree at
`get_default_log_dir() / SMOKE_CYCLE_NAME` and embeds any line prefixed `"Screenshot: "`.

### Screenshots

`logs.py` exposes three handler factories:

- `create_just_log_error(*, logger)` — failure handler, logs the error.
- `create_just_log_success(*, logger)` — success handler, logs the message only.
- `create_log_success_and_take_screenshot(*, driver, logger)` — success handler, logs **and** captures one `PASS` screenshot.

Bind the screenshot factory as `log_and_screenshot` — the name describes what the handler does, not when it is used.

**Rules:**

- **Every `drive_page` produces at least one `log_and_screenshot`.** A `drive_page` models one page's worth of work and almost always ends by
  submitting / navigating / verifying — it _is_ a page transition. The report's screenshot sequence must let a reader replay the journey `drive_page`
  by `drive_page`; "one screenshot per scenario" collapses a multi-page journey into a single still. (Pre/post fragments are the exception:
  setup/teardown is not the journey being proven — `login_as_demo_user` uses plain `log_success`.)
- **One screenshot per `drive_page`, on the act that shows its resulting state** — the terminal act in almost every case (the submit, the navigation,
  the verify).
  - When the terminal act is pure glue whose destination is the _next_ `drive_page`'s subject (a "click through to homepage" that the next
    `drive_page` then verifies), screenshot the most meaningful earlier act instead — the one that captures _this_ `drive_page`'s page.
  - Never screenshot a mid-fill act (selecting a dropdown, typing into a field). Same page, no state change.
- **Exception — a `drive_page` that drives a _component_, not a page.** When `drive_page` wraps a component interaction (driving the `Sidebar`,
  toggling a widget), don't apply the per-`drive_page` rule mechanically — and don't reflexively skip it either. Screenshot when **either** holds:
  - The interaction is itself a _visible_ part of the journey — a sidebar sliding in, an overlay opening, a panel expanding. The user saw that frame;
    the report should have it. A visible component change is as much "the journey" as a navigation.
  - It produced a page state worth a frame that an adjacent `drive_page` doesn't already capture.

  Skip only when the interaction is invisible (no on-screen change) **or** redundant with an adjacent frame — e.g. a logout `drive_page` driving
  `Sidebar` that lands on the homepage immediately before a `drive_page` which verifies that homepage. The question is never "is this a `drive_page`?"
  but "did the user see something here that the journey would otherwise miss?"

- **No manual failure shots.** `autoscreen_on_fail=True` is set on the `TestSuite` adapter and fires a burst of 4 shots on any failure. The burst is
  intentional (catches transient UI states like toasts and flash messages) — do not add manual fail screenshots.

## Scenario fragments

Reusable pre/post-conditions live under `src/tests/scenarios/_fragments/`. Wire them via:

- `pre_test_scenarios_fragments=[fragment_fn, ...]` — before the main scenario chain.
- `post_test_scenarios_fragments=[fragment_fn, ...]` — after.

A fragment has the scenario shape `(driver: WebDriver, logger: ILogger) -> list[ChainRunner]`. The framework concatenates pre + scenario + post into
one `ChainRunner` sequence.

Current: `login_as_demo_user` (`_fragments/auth.py`) authenticates as John Doe — used by every test that needs an established session as a
precondition.

### When to extract a fragment

- **Don't extract preemptively.** Two scenarios sharing 3 acts is a coincidence. Wait for **3+ scenarios** with the same block.
- **The block must be a precondition/postcondition, not the focus of any test.** `valid_login.py` does not use the login fragment — login _is_ the
  test there, and uses `log_and_screenshot` for the meaningful page transition. The fragment uses plain `log_success` because login-as-setup is not a
  journey frame in callers' context.
- **Unhappy-path login tests stay self-contained.** `failed_logins` and `unauthenticated_history_access` don't use the fragment — they must stay
  independent of demo-user state.

## Data-driven tests

When several scenarios share the same flow and only inputs vary, generate them from a dataset. Pattern (mirrors `ocarina-example/.../multi_login.py`):

1. **Dataset** — frozen dataclass + a `Sequence[Case]`. A separate module under `<feature>/datasets/<name>.py` when reused; inline in the scenario
   file when tiny.
2. **Scenario factory** — `_create_<name>_scenario(case: Case) -> SeleniumTestScenario` returns the closure binding the case into the chain.
3. **Test list comprehension** — `<feature>_tests = [create_selenium_test(name=…, test_scenario=_create_…(case)) for case in cases]`.
4. **Suite wiring** — unpack: `tests=[*<feature>_tests, …]`.

Current: `book_appointments.py` + `datasets/booking_cases.py` (Hongkong/Tokyo+readmission/Seoul; `apply_readmission` adds one conditional verify act);
`failed_logins.py` (inline dataset); `logout.py` (inline `logout_cases` — sidebar link vs logout URL).

### When to use it

- **Same flow shape, varying parameters.** Identical `drive_page` structure differing only in input values is a candidate. Three is a clear win.
- **Don't force it when terminal-step semantics differ a lot.** The booking dataset works because the readmission branch is one conditional act; if
  every case needed a bespoke verification chain, the list comprehension would hide more than it expressed.
- **Test names come from the data.** Use a `_test_name(case)` helper or an f-string so the name is meaningful in `pretty_print_results` output. Match
  the original per-file test names where possible to keep PR diffs small.
- **Test names must not contain `/` or `\`.** Ocarina writes the test name as a filename; either slash creates a missing subdirectory and the run
  fails at step 1 with `[Errno 2] No such file or directory`. Use `-` (e.g. `back-forward`, not `back/forward`).
- **Failure cases share the suite, not the structure.** `unauthenticated_history_access` lives next to `failed_logins` in the `Failure modes` suite
  but stays its own file — its flow has nothing to do with a login submission.

## `SeleniumBackAndForwardNavigationMixin` — shared back/forward navigation

Any POM needing back-button navigation mixes in `src/lib/ext/ocarina/adapters/selenium/browser_navigation.SeleniumBackAndForwardNavigationMixin`
rather than duplicating the `pre_url` capture + `driver.back()` / `driver.forward()` + `ec.url_changes` pattern. Place before `SeleniumTitleMixin` in
the MRO:

```python
class MyPage(SeleniumBackAndForwardNavigationMixin, SeleniumTitleMixin, POMBase):
    ...
```

`navigate_back()` captures the current URL, calls `driver.back()`, waits with `ec.url_changes(pre_url)`. `navigate_forward()` does the same with
`driver.forward()` but silently swallows `TimeoutException` — a server-side 302 during a prior `back()` may collapse the forward entry; a no-op
forward is not a failure. Both return `Self`.

## Conventions

- **Read the FRD first.** Element IDs, form field order, URL paths come from `CURA_FRD.md`.
- **No env vars / dotenv.** CURA is a public demo; the URL and credentials live in `src/constants/` and are imported.
- **URLs go in `src/constants/urls.py` as full URLs.** Never inline a URL in a scenario, page, or connector. POMs take a single
  `url: str = <DEFAULT_URL>` parameter, defaulted to the constant. Scenarios construct pages with just `Page(driver=driver)` and pass `url=...` only
  to override. Same rule for shared fixture data (credentials, hardcoded names) — extract to `src/constants/<topic>.py`.
- **Opinionated CLI keys.** Never rename keys read from `SeleniumCliStoreSingleton` (it's `"workers"`, not `"max_workers"`).
- **Log factories, never inline lambdas.** `.failure(log_error("msg"))` / `.success(log_success("msg"))`.
- **`TYPE_CHECKING` guard.** All type-only imports live inside `if TYPE_CHECKING:`, after all runtime imports.
- **`transient_errors`.** Add types here only when they should auto-retry. Deterministic findings (e.g. `BackForwardCacheExposureError`) never go
  here.
- **No dead connectors.** A connector function must be used in at least one scenario; speculative ones are caught in review.
- **No direct HTTP calls.** The suite tests through the browser. Raw HTTP (`requests`, `httpx`, `curl`) is out of scope unless a direct call is the
  only way to functionally exercise a specific user path (state seeding the UI can't produce). When in doubt: if a real user can do it through a
  browser, do it through a browser.
- **POM encapsulates page mechanics.** Don't expose multi-step UI (`open_nav` then `click_link`) to scenarios. Merge into one POM method (e.g.
  `logout()` opens the nav and clicks the link internally).
- **No FRD references outside `#` comments.** Test names, log messages, exception messages, docstrings — none contain `FRD §x.x`. Those references
  belong in `CURA_FRD.md` and in inline comments. The FRD number means nothing to someone reading a test report.

## Hard-won rules

Each rule statement leads. History and forbidden footguns follow only when load-bearing.

### Verify SUT behaviour — don't theorise

CURA is open source. Before building on a server-side claim, read the PHP:

```bash
gh api repos/katalon-studio/katalon-demo-cura/contents/<file>.php --jq '.content' | base64 -d
```

When to read it:

- A test fails on a claim you can't observe from the browser (CSRF mechanics, session lifecycle, redirect logic, validation rules).
- A code comment asserts _"CURA does X"_ and is load-bearing for a workaround.
- You're about to add a workaround based on what you _think_ CURA does.

Don't reach for the PHP for things the browser already tells you (rendered HTML, visible errors, URL changes) or things the FRD already documents.

When a comment asserts a load-bearing behaviour, confirm against the PHP and cite the file/function inline. If the claim is wrong, fix the test and
the comment in the same change.

**Forbidden as workarounds for hypothesised behaviour:** `driver.delete_all_cookies()`; `driver.refresh()` / `location.reload(true)` to "bypass
cache"; query-string cache-busters (`?_=<ts>`); session-reset rituals (logout-then-relogin) "to refresh the CSRF token"; any browser-state
manipulation a real user wouldn't perform. A real user logs out by clicking logout and logs back in by filling the form — nothing more. If the test
needs more than that to pass, the test is wrong or the SUT is broken; in the second case the test should fail (and document the gap), not paper over
it.

_History:_ a propagated `"CSRF token consumed after first booking"` comment seeded multiple such workarounds; the deployed login form has no CSRF
token at all.

### Inspect the SUT for security / spec gaps

This is the **encouraged** use of source inspection. CURA is full of gaps — no CSRF on deployed forms, no server-side input validation, no booking
uniqueness check, history rendered in submission order instead of by date, `session_destroy()` without cookie expiry, `$antiCSRF->isValidRequest()`
called against an undefined variable — most invisible from the browser. The PHP tells you the difference between a correctly-enforced rule and a
coincidence.

Proactively read it when:

- Adding or revising a gap test — read first, then write the test against the _actual_ mechanism so the failure message matches reality.
- A gap test passes when you expected it to fail (or vice versa) — find out whether CURA, the deployment, or the test scaffolding changed (cf.
  `IDENTIFIED_GAPS.md` §A-ENV-1).
- A test comment makes a load-bearing claim about server-side behaviour.
- You spot a bug pattern in one file (e.g. an undefined `$antiCSRF` in `appointment.php`) — grep the rest for the same pattern.

Every gap goes into `IDENTIFIED_GAPS.md` and, if user-facing, a `CURA_FRD.md` §9.x. The point is that a future reviewer doesn't have to re-derive what
we already know.

### Security testing is functional and static — never active

This is a **functional** test suite. Its scope ends at _what a real user can do through the browser_, plus _reading source for gap analysis_. Inside
that scope:

- Static analysis is welcome and encouraged (the previous rule).
- Functional tests that exercise security-relevant behaviour through the **normal UI/HTTP path** — submitting an empty visit date through the real
  form, attempting a duplicate booking through the real form, asserting no CSRF input by reading the rendered HTML, checking that the back-button
  doesn't expose a logged-out view by pressing back — are fine.

**Forbidden, no exceptions:**

- Crafted attack payloads of any kind: SQL injection strings, XSS / HTML / JS payloads, command injection, header/parameter pollution, path traversal,
  deserialisation payloads.
- Token tampering, signature stripping, cookie forgery, session-fixation attempts, forced-browsing fuzzers.
- Cross-origin POSTs constructed outside the suite, scripted directory enumeration, DOS, rate-floods — anything that escalates from "use the app like
  a user" to "attack the app like an adversary".

The line is intent and shape: a functional test uses the application the way the UI permits; an active security test fabricates inputs the UI would
never produce. "We tested that CURA accepts a duplicate booking" — fine. "We tested `' OR 1=1 --` in the username field" — not this project. Active
security testing belongs in Burp / ZAP / sqlmap / a dedicated engagement.

### Throwaway probes — when source-reading and the suite don't agree

A **probe** is a one-off script that drives the browser (or raw HTTP) through a suspect flow and prints concrete runtime state (URL, page title, form
HTML, hidden inputs, cookies, inter-request timings, network events). It **bypasses the Ocarina workflow entirely** — no `create_selenium_test`, no
suites, no campaigns, no assertions. Probes live in a gitignored directory, are **never committed or pushed**, and are deleted once the answer lands
in a durable artifact.

Reach for one when the framework's error surface doesn't show enough — a bare `TimeoutException` or `AssertionError` you can't act on. The trigger is
the visibility gap, not where you are in the test lifecycle:

- **Before** authoring a new test, when the behaviour you're about to assert against is load-bearing and you don't fully trust your model. Probe
  first; design the test around what you saw.
- **During** authoring, when the scenario keeps flaking and the failure mode shifts run-to-run. Stop tuning waits in the dark; print state at each
  step.
- **After** a regression, when the diagnostic points at a symptom (timeout, missing element) but doesn't explain it. Find out whether the SUT changed,
  the deployment drifted, or a parallelism artifact crept in.
- Whenever you suspect a deployment-vs-source discrepancy (GitHub source says X, the live HTML appears to do Y).

A probe is **not** a test (no assertions, not in CI, not parallel-safe), not a long-lived artifact, not something to commit. The output is the
_answer_, not the script — once the answer lands in `IDENTIFIED_GAPS.md`, `CURA_FRD.md`, a new test, or a source-cited comment, delete the probe.

### A probe must exercise the _exact_ target the code under test will use

A probe's value is that it removes inference. So it must not _contain_ one. "Exact target" means **all** of: exact locator, exact screen / page state,
exact wait condition, exact action.

- **A locator is half a location — the screen is the other half.** The same selector on two screens is two different targets:
  `By.CSS_SELECTOR, "button[type='submit']"` on the login page ≠ the same on the appointment page.
- **Never infer from a probe written for a different element/screen/use-case.** Real slip from this codebase: an Enter-on-button probe used
  `button[type='submit']` while the dispatcher it validated used `By.ID, "btn-book-appointment"`. "Probably the same button" is the exact inference
  the probe existed to kill.
- **Same locator, same screen, same condition, same action.** If the code uses `By.ID, "x"` with `element_to_be_clickable` and `Keys.ENTER`, the probe
  uses the same three. "Close enough" leaves a hole exactly where you needed certainty.
- **One probe, one question, one target.** Reusing a probe for a second target means editing it to the new exact screen/locator/action and re-running
  — not reading the old output.

A probe result is evidence only for what the probe literally did.

### Don't propagate a previous run's diagnosis without re-deriving it

Logs, screenshots, and prior comments describe a _past_ failure. For a _current_ failure, treat them as hypotheses to test, not conclusions to
inherit. Re-derive the cause from this run's evidence (current screenshot, current network response, current PHP) before reaching for the
previously-tried fix. One extra check is cheap; stacking workarounds on a wrong diagnosis is what ends in a reboot.

### Probe sequences vs ritual workarounds — multi-action "dances"

A scenario sometimes needs a long chain that doesn't map to a single user intent: log in → page A → page B → log out → press back → assert; or book →
log out → log back in → book again → check history. Call any such chain a **dance**. Two kinds, and the difference matters.

**Probe sequence (legitimate).** The dance _is_ the test. Removing any step changes what's being tested.

- `Logout - Session holds under back-forward stress (3 cycles)` — log out, then hammer back/forward against the history page N times; a single
  back-press can miss a cache edge case that only surfaces once the cache has been hit and re-hit.
- `Appointments - Saturation` — 5 sequential bookings _in one session_ probes whether CURA imposes any per-session rate limit. Repetition is the test.
- `History - Empty state on fresh login` → `click 'Go to Homepage'` → `verify homepage` — the click-through is REQ-HIST-4's specified path.

**Ritual workaround (not legitimate).** Glue around a _hypothesis_ about SUT behaviour. Symptoms:

- The justifying comment asserts a SUT behaviour ("CSRF token consumed after first booking", "logout doesn't expire the cookie so we must clear
  cookies") that was never verified against the PHP.
- Removing the step doesn't change _what_ the test exercises, only whether it works.
- The dance touches browser state a real user wouldn't (`delete_all_cookies()`, `location.reload(true)`, query-string cache-busters, manual
  session-cookie expiry).

**When you write a dance,** ask: if a user did exactly this sequence by hand, does each step have a reason from their perspective? Yes → probe
sequence, keep it, document the _concern being probed_ in the scenario docstring. No → stop, read the PHP, fix the underlying assumption.

The same physical action can be a probe in one test and a workaround in another — intent, not gesture. _logout→relogin as the focus of a
session-integrity probe_ → probe sequence; _logout→relogin between two bookings to "refresh the CSRF token"_ → ritual workaround (removed; the CSRF
theory was unsupported by the PHP).

### A cross-browser behavioural difference is a finding, not a test to route around

When a test passes on one browser and fails on another, the divergence **is the result** — that's what the multi-browser matrix exists for. **Never
skip a test on the browser where it fails.**

Investigate which side of the line the failure is on:

- Real user-facing defect → the test is gold; stays red until the app is fixed; finding goes in `CURA_FRD.md` / `IDENTIFIED_GAPS.md`.
- Genuine browser/driver interaction defect → document in `IDENTIFIED_GAPS.md`, keep the test. A red cell that means something beats a green cell that
  lied.
- Test scaffolding that only works on one browser → the one case where you fix the _test_ — but you fix it to work on **both**, never by removing it
  from one.

"Passes everywhere except Chrome" is not a reason to stop running it on Chrome. It is a reason to find out why.

### Functional testing simulates a real human — ask "would a real person hit this?"

Every test here stands in for a person clicking through CURA in a browser. When a test fails — especially on one browser only — the decisive question
is not "why is the automation unhappy?" but: **would a real person, doing exactly this in this browser, hit the same wall?**

- **Yes** → real user-facing defect. The test is doing its job.
- **No — only the synthetic automation path is affected** (the driver's synthetic `.click()` does nothing, but a fresh re-find / keyboard submit /
  ActionChains / CDP trusted click all work) → tool artifact. Fix in the test/POM, not in a bug report against the app.

Answer it empirically: escalate from synthetic toward real — synthetic `.click()` → fresh re-find → keyboard submit → ActionChains move-and-click →
CDP trusted input event — and watch where it starts working. The boundary tells you the side of the line. Don't conclude by reasoning.

### Confirming a back-forward-cache exposure — the back-then-reload check

A page served from the browser's back-forward cache (BFcache) is restored from a local snapshot with **no server round-trip** — any server-side access
control (logout redirect, session check, auth gate) never runs. After `driver.back()` lands on a page that should be inaccessible, the URL alone
cannot tell you whether the server _allowed_ it or the browser served a _cache_.

**`back()` → `refresh()`.** A reload always reaches the server, unlike back-navigation. If `back()` did not redirect away but `refresh()` does,
`back()` served a BFcache snapshot — the server's invalidation is intact; only the cache layer exposed the stale view. If `refresh()` also fails to
redirect, the server itself isn't invalidating — a worse, separate finding. Two outcomes, two distinct failure messages.

This is the one place `driver.refresh()` is legitimate. The "load-bearing SUT behaviour" rule forbids `refresh()` _inserted to paper over_ a flaky
test ("reload to bypass cache and hope it passes"); here `refresh()` **is the instrument of the assertion** — the thing that separates the two causes.
Intent is the dividing line.

**A confirmed BFcache exposure raises a dedicated, non-transient exception** — `BackForwardCacheExposureError` (`src/lib/errors.py`). Never a bare
`AssertionError`; never a Selenium `WebDriverException`. The finding is deterministic and must never land in `transient_errors` (and so must never
surface as an auto-retried `TimeoutException`). Catch Selenium's `TimeoutException` from the reload-wait and re-raise as the dedicated type. The
exception name in the report _is_ the diagnosis.

BFcache eligibility varies by browser and version — some browsers admit even `no-store` pages to BFcache; others honour `no-store` and re-request.
That divergence is the matrix's job to surface. `HistoryPage.verify_back_button_did_not_restore_view` is the worked example, split across
`post_logout_bfcache_exposure` and `post_logout_server_invalidation`.

### Scenario file structure

**One scenario per file.** Hand-written multi-scenario files are not allowed — split them. The only exception is **data-driven families**, where a
factory generates N tests from a `Sequence[Case]` (e.g. `failed_logins.py`, `book_appointments.py`) and lives in one file because the flow is shared
and only inputs vary.

**Top docstring gives the flow as arrows.** A reader must know exactly what the file exercises before reading any code. The arrow form
(`open page → fill form → submit → verify confirmation`) is the same mental model as the scenario itself (chained `act()` calls). The docstring also
lists pre/post-fragments and any setup/teardown specific to the file. If a section has none, write `(none)` — explicit "no setup" is information.

```python
"""Book an appointment and verify it lands in history.

Flow:
  open appointment form → fill (facility, program, date, comment) → submit
  → verify confirmation → open history → verify booking card matches input

Pre-fragments: login_as_demo_user
Post-fragments: (none)
"""
```

```python
"""Data-driven booking — one test per row in `booking_cases`.

Flow (each case):
  open appointment form → fill (case.facility, case.program, case.date, case.comment) → submit
  → verify all confirmation fields match the case
  (readmission cases insert verify_readmission_on_confirmation after facility)

Pre-fragments: login_as_demo_user
Post-fragments: (none)
"""
```

**All `create_selenium_test()` at the bottom.** When a file declares more than one test, group all scenario-builder functions first and all
`create_selenium_test(...)` assignments at the bottom in one block. Never interleave scenario → test → scenario → test. A reader should be able to
glance at the bottom and see the file's public surface — names, fragments, wiring — without scanning every scenario body.

```python
def _scenario_a(driver, logger): ...
def _scenario_b(driver, logger): ...
def _scenario_c(driver, logger): ...

test_a = create_selenium_test(name="...", test_scenario=..., pre_test_scenarios_fragments=[...])
test_b = create_selenium_test(name="...", test_scenario=..., pre_test_scenarios_fragments=[...])
test_c = create_selenium_test(name="...", test_scenario=..., pre_test_scenarios_fragments=[...])
```

### POM selectors live at the top of the class

All locator tuples (`_xxx = (By.ID, "...")`, etc.) belong in one block at the top of the POM class, immediately after the docstring and before
`__init__`. No locators declared further down next to the method that uses them. A POM's selectors are its contract with the DOM; one place means a
reader updating an element ID, auditing for fragility, or grepping finds them instantly.

```python
@final
class HistoryPage(...):
    """..."""

    _section = (By.ID, "history")
    _appointment_cards = (By.CSS_SELECTOR, ".panel.panel-info")
    _empty_message = (By.XPATH, "//*[normalize-space()='No appointment.']")
    _btn_go_homepage = (By.XPATH, "//a[normalize-space()='Go to Homepage']")

    def __init__(self, *, driver: WebDriver, url: str = HISTORY_URL) -> None:
        ...
```

### Always use WebDriverWait — never raw find_element

Raw `driver.find_element()` and `find_elements()` snapshot the DOM at call time. If the page is still rendering or running Bootstrap/jQuery init, the
call either raises `NoSuchElementException` or returns a stale element — intermittent and hard to reproduce.

**Every POM method that locates an element goes through `WebDriverWait`.** Pick the expected condition for the intended use:

| Use case                                       | Pattern                                                                                                          |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Click a button, checkbox, link, or select      | `WebDriverWait.until(ec.element_to_be_clickable(locator))`                                                       |
| Send keys to a text input                      | `WebDriverWait.until(ec.element_to_be_clickable(locator))`                                                       |
| Pass element to `execute_script` (JS exec)     | `WebDriverWait.until(ec.presence_of_element_located(locator))`                                                   |
| Read `.text` from a label or heading           | `WebDriverWait.until(ec.visibility_of_element_located(locator))`                                                 |
| Wait for a page section to exist               | `WebDriverWait.until(ec.presence_of_element_located(locator))`                                                   |
| Assert element transitions visible → invisible | `WebDriverWait.until(ec.invisibility_of_element_located(locator))`                                               |
| Assert access-control redirect                 | `WebDriverWait.until(ec.url_changes(self._url))` — URL check, no DOM, no implicit wait                           |
| Assert DOM absence on a fully-loaded section   | `driver.execute_script("return document.querySelectorAll('…').length")` — synchronous JS, bypasses implicit wait |

**`invisibility_of_element_located` only works fast when the element _exists_ at navigation time and then disappears** (form closes after submit,
spinner hides). When the element never existed (e.g. `#history` on the login page after redirect), Selenium 4 still fires the full implicit wait on
each poll before raising `NoSuchElementException`. Use `ec.url_changes` for redirect checks and `execute_script` querySelectorAll for static DOM
absence.

**Implicit wait is set by the CLI (`--wait-timeout`).** Never read, modify, or work around it in POM/test code — it is framework infrastructure. No
`driver.implicitly_wait(...)` outside the Ocarina driver builder.

**Exception: `find_elements` (plural) for multi-element reads after `verify()`.** When `verify()` has confirmed the section is loaded, subsequent
`find_elements` on child elements of that section is safe (CURA pages are server-rendered, so all children are present when the landmark element is).

**Not an exception: "this page is static / already loaded / verify() ran first."** Don't skip `WebDriverWait` on reasoning about a specific page. The
rule is a principle, not a per-page observation; "exceptions by reasoning" reintroduce the flakiness the rule exists to prevent. The two above are the
only valid ones.

### Widget-decorated inputs: drive the widget's API, don't fight its intercepts

When a third-party widget decorates a plain `<input>` (datepicker, autocomplete, masked-input, rich-text editor, etc.), its own keyboard/click
handlers intercept `send_keys`, click-outside, focus changes, and any Selenium-level interaction. Fighting those intercepts yields a fragile sequence
(type → escape → tab → click around the overlay → hope).

The pattern: bypass the widget's user-facing interface and drive its scripting API. Set the underlying field value via JS, then call the widget's
update/hide hook so the widget reflects the new state. The form sees a normal `<input value="...">` on submit; the widget doesn't fight you because
you went through its own API.

Corollary: when a widget can render an overlay on top of nearby elements, fill the widget-backed field _last_, or close the widget before interacting
with the next field.

Example: CURA's `txt_visit_date` Bootstrap 3 datepicker — see `AppointmentPage.enter_visit_date` for the JS + widget-API call.

### Setup/teardown actions: prefer the URL, save the UI click for the test that owns it

When a feature has a URL-level entry point (a GET that performs the action server-side and returns a known target page) and the same feature is
reachable via a UI element wired through scripted event handlers:

- **Tests where the action is incidental** (pre/post-fragments, intermediate state transitions) use the URL. `driver.get(<action_url>)` is direct, has
  no event-handler dependency, and blocks until the server's redirect lands.
- **Tests where the action is the subject under verification** ("the sidebar link still works", "the submit button still routes correctly") click the
  UI element, because _that path_ is what they assert.

This keeps unrelated tests focused while preserving a dedicated test that owns the UI path and fails loudly if event wiring breaks.

Example: `Sidebar.logout()` uses `driver.get(LOGOUT_URL)` because logout is teardown in every test except one; `Sidebar.logout_via_sidebar()` drives
the real `#menu-toggle` → Logout-link click and is used by exactly one test, `logout.py`, which owns that path.

**Watch the justification, not just the split.** `logout()` originally carried "a jQuery dispatch race that proved unreliable in headless Chrome" —
and that was false. A probe drove the exact sidebar path in clean headless Chrome (password manager off, as `create_drivers_pool.py` builds it) and it
worked 5/5; the "race" was the Chrome password-breach modal swallowing the click, the same misdiagnosis as the Enter-on-button case (see "Form
submission paths"). The URL-for-teardown split is still right — but on its real merit (a direct GET is the most reliable way to _reach_ a post-action
state), never on an invented browser bug. If you write "prefer the URL because the UI path is flaky", prove the flakiness with a probe first or don't
claim it.

### Shared UI components live in `pages/components/`, named for the component

Some UI is not a page — it is chrome rendered on _every_ page (a sidebar, a header, a cookie banner, a global modal). It has no URL, isn't a
navigation target, and parking its actions on one arbitrary page object (or in a vague `commons.py` grab-bag) misleads every reader about where that
behaviour belongs.

Model each such component as its own POM under `src/pages/components/`, **named for the component**, not for its role:

- `pages/components/sidebar.py` → `class Sidebar` ✓
- `pages/components/commons.py`, `pages/components/shared.py`, `pages/components/misc.py` ✗ — "Commons" is not a thing on the screen; `Sidebar` is. A
  grab-bag filename invites a grab-bag class.

One component, one file, one class. A component POM still subclasses `POMBase` (+ `SeleniumTitleMixin`); `verify()` checks the component is present
(e.g. `Sidebar` verifies `#menu-toggle`). Connectors live in `connectors/test_steps/<component>.py`, mirroring the filename. Worked example: `Sidebar`
owning `logout()`, `logout_via_sidebar()`, and the nav-link methods.

### TYPE_CHECKING imports must be verified against the actual module

With `ignore_missing_imports = true` in `pyproject.toml`, mypy will not flag a wrong import path inside a `if TYPE_CHECKING:` block — the name
resolves nominally at type-check time and never runs, so typos and wrong-module references persist silently. Verify any new `TYPE_CHECKING` import
against the actual module's public API rather than copy-pasting from a similar-looking module.

Example: in this project, `ILogger` lives at `ocarina.ports.ilogger`, not at `ocarina.custom_types.logger` (that module does not exist).

### ChainRunner collections — `Sequence` by default, `list` only when you mutate

A scenario / fragment / step builder _produces_ an ordered run of chain runners; the consumer iterates. That is exactly what
`Sequence[ChainRunner[Any]]` says. `list` carries an extra mutability promise we don't deliver and consumers don't need; `tuple[X, X]` claims a fixed
arity that nothing downstream relies on (the runner just flattens it). Both narrow the type past the actual contract and read as accidental.

Defaults:

- **Function return types, parameter annotations, struct fields:** `Sequence[ChainRunner[Any]]`. The pre-existing `TestChain` alias
  (`ocarina.custom_types.test_components.TestChain = Sequence[ChainRunner[Any]]`) is the same shape — use it where convenient.
- **Local buffers you actually mutate** (`.append`, `.extend`, in-place sort): `list[ChainRunner[Any]]`. mypy will tell you when you've lied —
  `Sequence` has no `.append`, so the annotation _is_ the check.
- **Never** `tuple[ChainRunner[Any], ChainRunner[Any]]` to mean "two chain runners I'm about to flatten". The pair-ness carries no meaning at the call
  site; write a list, annotate `Sequence`.

Example: [`saturation_booking._book`](src/tests/scenarios/appointment/saturation_booking.py) returns `Sequence[ChainRunner[Any]]` (caller iterates);
[`post_logout_frenetic_navigation`](src/tests/scenarios/login/post_logout_frenetic_navigation.py) declares `steps: list[ChainRunner[Any]] = [...]`
because it then `.extend()`s the list inside a loop.

### Alias imports that shadow a kwarg or local name

When the same identifier is both a kwarg of a function you call and the name of a function/symbol you import, the import shadows the kwarg in your
module and produces confusing call-site errors. Alias the import under a private name (`_xxx`).

Example: `main.py` imports `from ocarina.opinionated.launcher.bootstrap import run_plugins as _run_plugins` because `bootstrap(run_plugins=...)` also
accepts a `run_plugins` kwarg.

### Long string literals — implicit concatenation

ruff enforces 88-char lines (`E501`). When a string literal in `.failure()` / `.success()` would exceed, split with Python implicit string
concatenation — adjacent literals separated by whitespace are joined at compile time:

```python
.success(
    log_success(
        "First part of the message "
        "continued on the next line"
    )
),
```

No backslash continuation, no `+` concatenation, no f-string tricks. Run `ruff format src/` after to normalise indentation, then `ruff check src/` to
confirm `E501` is resolved.

### Form submission paths — and verifying _why_ one "doesn't work"

Three interactions submit a form, all legitimate browser behaviour and all valid dispatcher paths: `element.click()` on the submit `<button>`;
`send_keys(Keys.ENTER)` on a focused text `<input>` (HTML implicit submission); `send_keys(Keys.ENTER)` on a focused `<button type="submit">`.

The one real caveat is a JS widget bound to an input that intercepts Enter — CURA's Bootstrap datepicker on `txt_visit_date` toggles its calendar on
Enter instead of submitting, so Enter-on-that-input is not a submission path (Enter-on-the-submit-button still is). See "Widget-decorated inputs".

**The hard-won part:** _"`send_keys(Keys.ENTER)` on a `<button>` is unreliable"_ was once treated as fact and propagated into three files — a
**misdiagnosis**. The Chrome password-breach modal was silently swallowing _all_ input after a login (clicks included); "Enter didn't submit" got
pinned on the interaction path rather than the modal. A probe later showed Enter-on-button submits 12/12 in a clean browser. Before you declare an
interaction path unreliable, find out _why_ it failed; a swallowed input, an intercepting widget, and a genuinely-bad path all look identical from
"the form didn't submit."

Which forms expose which dispatchers is per POM and documented in `CURA_TEST_STRATEGY.md` §4.

### No magic numbers — least of all in log messages

A magic number is a bare literal whose meaning isn't obvious from a name. Two rules, the second stricter:

1. **In code:** a literal carrying meaning — a count, an offset, a threshold — gets a named constant. Genuinely arbitrary values are allowed (a date
   offset just needs to be "far enough out") but justified in a comment and kept as implementation detail.
2. **In log / `success` / `error` / screenshot messages: never.** A hardcoded number in a log line is the surest way to produce a stale, noisy log:
   the message says `5` while the code does something else, and the reader trusts the message. It also adds nothing — the log already enumerates the
   events. A reader seeing five `Booking confirmed` lines knows it happened five times; writing "5" into a sixth line is dead weight. If a quantity
   genuinely must appear, interpolate the named constant (`f"... {_SATURATION_COUNT} ..."`) so it can't drift — but first ask whether it needs to be
   there. Usually not; let the log's own line count speak.

**A message must never claim more than its `act` verified.** A `.success(...)` line states exactly what the `act` it hangs off just checked — no more.
"All N bookings recorded" is a lie if the assertion only confirmed one of them (this was a real bug: a saturation test whose check proved "facility
appears ≥ once" while its message announced "all 5 recorded"). If you want the message to say "all N", the assertion behind it must verify all N. An
overstated message is worse than no message, because the reader believes it.

### Use the constant — never retype its value

A value bound to a named constant or variable belongs everywhere by that name: in code, in messages, in test names, in fixtures. Retyping the literal
duplicates the source of truth — change the constant, miss one of the copies, and the suite quietly contradicts itself. That is what variables _exist
for_.

_Example:_ `valid_login.py` imports `DEMO_USERNAME` and uses it correctly in `login_with_credentials(DEMO_USERNAME, DEMO_PASSWORD)` and in
`f"Submitted login as {DEMO_USERNAME}"` — but the test name slipped through as `"Valid Login - John Doe"`. Wrong; should be
`f"Valid Login - {DEMO_USERNAME}"`.

The one exception is the constant's own definition (`DEMO_USERNAME = "John Doe"` — by definition the literal lives there). Everywhere else
interpolates. If you find yourself typing a value that already has a name in scope (or one easily added to `src/constants/`), use the name — or add
one.

### Datasets are authoring decisions — stop and ask before running

A test dataset is not implementation detail. It is a deliberate authoring decision about _what_ to exercise: which facility, which date, which
credentials, which combination of fields, which edge values. Those choices belong to the user, not to whoever happens to be typing.

**When you create or modify a dataset, do not run the tests automatically.** Stop, report what you added or changed ("I built these cases: X, Y, Z; I
changed Q from A to B"), and wait for the user to review and approve — _then_ run. This applies to anything that is meaningfully _test input_:

- explicit case tuples (`booking_cases`, the inline `logout_cases`, `failed_logins` cases),
- lists of values used as test data (`_VISIT_DATES`, batch-booking dates, dataset matrices),
- module-level constants used as test inputs (`_FACILITY`, `_PROGRAM`, `_DATE`, `_COMMENT`, comments embedded in submissions),
- new credentials or usernames if any are ever added.

Mechanical refactors that don't change the data (renaming a field, reordering, restyling) don't trigger this — only changes to _what is being tested_.
When in doubt, treat it as a dataset change and ask.

A silent dataset choice plus a green run looks like "I ran the tests successfully" while quietly imposing the author's idea of coverage on the user.
Stopping surfaces the decision.

### ruff `select = ["ALL"]`

Common rules to know:

- `TC002` / `TC003` — runtime imports must not be in `TYPE_CHECKING` blocks.
- `S105` — hardcoded passwords flagged; suppress with `# noqa: S105` on credential constants.
- `D401` — docstrings in imperative mood ("Build…" not "Builds…").
- `ANN` — return type annotations required on public functions.

## Dev setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install . ruff mypy mypy-extensions typing-extensions pre-commit
pre-commit install --config .pre-commit-config.yaml
```

## Quality checks

```bash
ruff format src/          # format
ruff check src/           # lint (select ALL — see pyproject.toml for ignores)
mypy src/                 # type check
pre-commit run --all-files --config .pre-commit-config.yaml
```

Run these before committing. The CI gate (`lint-and-typecheck`) runs the same checks.

## CI workflows

| Workflow           | Trigger                         | What it does                                                                                             |
| ------------------ | ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `ai_proof_ci.yml`  | every PR touching `ai_proof/**` | Lint + typecheck (`ruff format` check, `ruff check`, `mypy`). Fast; gates merges.                        |
| `ai_proof_e2e.yml` | manual (`workflow_dispatch`)    | Full cycle on a Firefox + Chrome matrix, `fail-fast: false`, `--workers 3`, uploads artifacts (30 days). |

The e2e matrix uses `fail-fast: false` — a Firefox failure doesn't abort Chrome. **Never collapse the matrix to a single browser** to "simplify" a
run; browser-specific back-navigation (BFcache, session) is exactly what the matrix catches. Both jobs must pass before calling the suite green.

The e2e workflow doesn't gate merges — it's explicit and expensive. To require it on a PR, dispatch from the branch and link the run in the PR
description.

## PR descriptions

Two required sections, every PR:

- **`## Summary`** — what changed and why, one short paragraph. Lead with the rule or pattern you applied, not the file list.
- **`## Test plan`** — checklist. `[x]` what you ran locally (`ruff format && ruff check && mypy`, full e2e cycle); `[ ]` what only the manual
  `ai_proof e2e` workflow can confirm (artifact upload, Firefox parity, fresh DOCX render). State the local result: `All N tests pass locally (X.Xs)`.
  The PR gate runs `lint-and-typecheck` only, so this is the sole functional signal until someone dispatches the e2e workflow.

### Hierarchy slice (when test boundaries shift)

Ocarina's `Cycle → Campaign → Suite → Test` hierarchy makes impact legible in two lines. When a PR adds, removes, relocates, or renames anything in
that hierarchy — including moving a test in or out of the smoke gate — render the affected slice as a tree under the Summary:

    Smoke (fail-fast gate):
      Prerequisites
        └─ Authentication baseline       (valid_login)

    Main:
      Authentication
        ├─ Session management             (logout)
        └─ Failure modes                  (failed_logins + unauthenticated_history_access)
      Appointments
        ├─ Booking                        (book_appointment_tests, data-driven)
        └─ History                        (view_history)
      User journeys
        └─ Cross-feature flows            (book_and_verify_history)

When only part of the cycle is touched, render only that part — but keep smoke visible if the change crosses the gate. Annotate name diffs inline
(`old → new`) inside the leaf node.

Skip the tree for changes that don't shift boundaries: constant extraction, POM cleanup, scenario-internal refactors, CI tweaks, doc-only changes.
Those are prose with a Summary and Test plan.

### Optional sub-sections

Use them when they earn their space:

- **Filesystem / Suites / Campaigns** — a short before-after when several files move at once.
- **CLAUDE.md** — when CLAUDE.md is touched, list the sections added or edited.
- **Net delta** — `Net: +N / −M lines, K fewer files` is more honest than "small refactor".

### Stacking and rebasing

When a PR's base branch is squash-merged, the dependent PR auto-closes (its base branch is deleted). Rebase the dependent branch onto the new `main`
and reopen — title and body can be reused as-is. Note in the new PR that it replaces the auto-closed one.
