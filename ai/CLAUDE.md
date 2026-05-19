# Ocarina Test Suite — Claude Context

Orientation for Claude (and any contributor) working in an Ocarina-based browser test suite. The hard couplings here are **Ocarina itself**, the
browsers it drives (Firefox, Chrome, Edge, Safari), and the host OSes (macOS, Windows, Linux). Everything else — the SUT's backend stack, the spec
format, the project layout — is interoperable and you should resist baking assumptions about it into rules.

References:

- Framework source: <https://github.com/mojo-molotov/ocarina>
- The Holy Book (docs): <https://github.com/mojo-molotov/ocarina-holy-book>
- Worked example, minimal: <https://github.com/mojo-molotov/ocarina-example>
- Worked example with gap inventory and AI proof: <https://github.com/mojo-molotov/ocarina-with-ai-example>

When a rule below cites a worked example, the link points into one of those two example repos. When a rule cites the framework itself, it points at
`mojo-molotov/ocarina`. When a rule cites the docs, it points at the Holy Book.

### The SUT in the worked examples

The hard-won rules below are illustrated against **CURA Healthcare**, the demo app exercised by `ocarina-with-ai-example`:

- Deployed: <https://katalon-demo-cura.herokuapp.com/>
- Source (PHP, open source): <https://github.com/katalon-studio/katalon-demo-cura>
- Demo credentials (public, hardcoded): `John Doe` / `ThisIsNotAPassword`

CURA is a small healthcare-booking app — login, appointment form, history, profile. It has documented behavioural gaps (no server-side date
validation, no booking uniqueness check, history ordered by submission, no CSRF token on deployed forms despite the source calling
`$antiCSRF->insertHiddenToken()`, `session_destroy()` without cookie expiry). Those gaps are the project's intentional-fail tests and the worked
examples throughout this document. Real SUT, real findings — not made-up illustrations.

## Project-shaped documents

A mature Ocarina project usually carries the following, under whatever names and formats the team prefers. The FRD source can be Markdown, JSON, Jira,
Confluence, PDF, OpenAPI — Claude is multi-modal; the format is interoperable, the rule is that the document exists and is the single source of truth
for its concern. (The rest of this document uses "FRD" as the standard QA term for this artifact; substitute whichever name your team uses.)

- A **README** — human-facing entry point (what it is, how to run, how to report).
- An **FRD** (Functional Requirements Document) — functional requirements, IDs, business rules, the known-defect catalogue. Read before writing or
  changing tests. (`CURA_FRD.md` in `ocarina-with-ai-example`; could be a Confluence page, a Jira epic, an OpenAPI spec, or a PDF in your project.)
- A **test-strategy doc** — taxonomy, expected pass/fail categories, the suite/campaign tree. Keep coverage tables and the hierarchy in sync with the
  code.
- A **gap inventory** — defects discovered while testing, each source-cited. Add an entry on discovery; remove on fix. (`IDENTIFIED_GAPS.md` in
  `ocarina-with-ai-example` is the canonical shape.)
- A **`CLAUDE.local.md`** — gitignored, machine-specific (driver paths, framework clones). Template below.

## Project philosophy

An Ocarina suite leans on strictness in every dimension a project chooses to apply it: maximal linter rules (Ruff `select = ["ALL"]` in
`ocarina-with-ai-example`), strict type checking, `--workers ≥ 2` in CI, a multi-browser matrix. The pressure exists to make the better solution
visible — and to make the hacky shortcut uncomfortable.

- **No tricks or hacks.** JS-clicks to skip hit-testing, lint suppressions to silence a rule, `time.sleep` to mask a race, `driver.implicitly_wait` to
  patch a timing bug. If a hack is genuinely the only option, document why no clean fix exists and mark it so a reader doesn't copy the pattern.
- **Teach the pattern, not the symptom.** A rule must read as reusable knowledge — _the behaviour to handle correctly_ — not a log of which browser,
  version, library, or POM showed the problem first. Symptom-bound names expire silently the moment they drift. Use concrete examples freely (CURA's
  specific gaps below illustrate every rule), but keep symptom names out of the rule statement itself; they belong in the call-site comment or in the
  gap inventory.

## CLAUDE.local.md template

`CLAUDE.local.md` is gitignored and stores per-machine paths. If it's missing, create it with the template below — and ask for the paths, don't guess.
`find ~/ -name chromedriver -type f 2>/dev/null` locates chromedriver on Unix-likes; Ocarina/example clones have no predictable location.

```markdown
# Local machine config

## chromedriver

Path: `/path/to/chromedriver`

## Ocarina source repos (git clones)

- **ocarina**: `/path/to/ocarina`
- **ocarina-example**: `/path/to/ocarina-example`
- **ocarina-with-ai-example**: `/path/to/ocarina-with-ai-example`
```

Use the clones to look up framework internals, public types, opinionated interfaces, and conventions. The Holy Book is authoritative for the
documented surface; the clones are authoritative for everything else.

## Ocarina hierarchy

`Test → TestSuite → TestCampaign → TestCycle`. `TestCycle` accepts `smoke_tests_campaigns=` (gate, fail-fast) and `campaigns=` (main); smoke runs
first and gates main.

A **scenario** builds a `list[drive_page(...)]`. Each `drive_page` chains `act()` calls with `.failure()` / `.success()` handlers from the project's
`logs.py` — never inline lambdas.

## Test strategy patterns

Whatever cycle name and shape a project picks, a few rules carry across:

- **"Smoke" is structural, not lexical.** Express the gate via `TestCycle.smoke_tests_campaigns=`; never put "smoke" in a name string.
- **Smoke is the minimum that proves the system is alive.** A test belongs in smoke iff its failure makes the rest of the cycle uninformative. A basic
  authenticated entrypoint usually qualifies; nothing else usually does.
- **Each main campaign is feature-shaped, not method-shaped.** Group by _what_ is being exercised; let each campaign expose `happy_paths` /
  `failure_modes` / `baseline` suites as needed.
- **Default mode is fail-fast.** Use `mode="wait-for-all-smoke-tests"` only if you genuinely need both smoke campaigns to attempt regardless of the
  first failing.

### Test duplication with `--workers`

With `--workers N`, Ocarina duplicates single-test suites up to N times to flush concurrency hazards (race conditions, session cleanup, driver reuse).
The `[COPY N]` annotations are not noise — they confirm the saturation framework is active. Expect them on small smoke suites; this is a feature.

## Running tests

```bash
python -u src/main.py \
  --driver-path <path/to/chromedriver> \
  --browser chrome \
  --workers 3 \
  --wait-timeout 10 \
  --logger terminal+file
```

- **Never `--workers 1`.** Single-worker runs mask concurrency failures and diverge from CI. Match the workers count to your CI matrix; CI is the
  canonical reference.
- **Use `python src/main.py`, not `python -m src.main`.** `src/` is the source root directory, not a package — script form correctly puts `src/` on
  `sys.path[0]` so intra-suite imports read `from constants.urls import …`, never `from src.constants.urls import …`. Don't package `src`. CI uses the
  script form.

CLI flags (all optional with defaults):

| Flag                             | Purpose                                                           |
| -------------------------------- | ----------------------------------------------------------------- |
| `--browser`                      | `chrome` / `firefox` always; `edge` on Windows; `safari` on macOS |
| `--driver-path`                  | Path to the matching driver binary                                |
| `--profile-path`                 | Browser profile directory to start from                           |
| `--not-headless`                 | Show the browser UI                                               |
| `--workers N`                    | Parallelism                                                       |
| `--wait-timeout`                 | Per-operation wait, seconds                                       |
| `--only ID …` / `--exclude ID …` | Filter tests by id                                                |
| `--logger`                       | `mute` / `terminal` / `file` / `terminal+file`                    |

Use `--logger terminal+file` when reports must be generated (the DOCX generator reads the log tree).

## Reports and screenshots

Every run writes into a gitignored reports directory (conventionally `.reports/`):

- **DOCX proofs** — `.reports/docx/<run-id>/` — one document per test, embedding a screenshot at every page transition.
- **JSON results** — `.reports/json/<uuid>.json` — machine-readable pass/fail.

Both come from `run_plugins` wired in `main.py` (via `generate_docx_proof` / `generate_json_results`). The DOCX generator reads the log tree and
embeds any line prefixed `"Screenshot: "`.

### Screenshots

The project's `logs.py` typically exposes three handler factories:

- `create_just_log_error(*, logger)` — failure handler, logs the error.
- `create_just_log_success(*, logger)` — success handler, logs the message only.
- `create_log_success_and_take_screenshot(*, driver, logger)` — success handler, logs **and** captures one `PASS` screenshot.

Bind the screenshot factory as `log_and_screenshot` — the name describes what the handler does, not when it is used.

**Rules:**

- **Every `drive_page` produces at least one `log_and_screenshot`.** A `drive_page` models one page's worth of work and almost always ends by
  submitting / navigating / verifying — it _is_ a page transition. The report's screenshot sequence must let a reader replay the journey `drive_page`
  by `drive_page`; "one screenshot per scenario" collapses a multi-page journey into a single still. (Pre/post fragments are the exception:
  setup/teardown is not the journey being proven — fragment scenarios use plain `log_success`.)
- **One screenshot per `drive_page`, on the act that shows its resulting state** — the terminal act in almost every case (the submit, the navigation,
  the verify).
  - When the terminal act is pure glue whose destination is the _next_ `drive_page`'s subject (a "click through to homepage" that the next
    `drive_page` then verifies), screenshot the most meaningful earlier act instead — the one that captures _this_ `drive_page`'s page.
  - Never screenshot a mid-fill act (selecting a dropdown, typing into a field). Same page, no state change.
- **Exception — a `drive_page` that drives a _component_, not a page.** When `drive_page` wraps a component interaction (driving a sidebar, toggling a
  widget), don't apply the per-`drive_page` rule mechanically — and don't reflexively skip it either. Screenshot when **either** holds:
  - The interaction is itself a _visible_ part of the journey — a sidebar sliding in, an overlay opening, a panel expanding. The user saw that frame;
    the report should have it. A visible component change is as much "the journey" as a navigation.
  - It produced a page state worth a frame that an adjacent `drive_page` doesn't already capture.

  Skip only when the interaction is invisible (no on-screen change) **or** redundant with an adjacent frame. The question is never "is this a
  `drive_page`?" but "did the user see something here that the journey would otherwise miss?"

- **No manual failure shots.** With `autoscreen_on_fail=True` on the `TestSuite` adapter, the framework fires a burst of 4 shots on any failure. The
  burst is intentional (catches transient UI states like toasts and flash messages) — do not add manual fail screenshots.

## Scenario fragments

Reusable pre/post-conditions live under `src/tests/scenarios/_fragments/`. Wire them via:

- `pre_test_scenarios_fragments=[fragment_fn, ...]` — before the main scenario chain.
- `post_test_scenarios_fragments=[fragment_fn, ...]` — after.

A fragment has the scenario shape `(driver: WebDriver, logger: ILogger) -> list[ChainRunner]`. The framework concatenates pre + scenario + post into
one `ChainRunner` sequence.

### When to extract a fragment

- **Don't extract preemptively.** Two scenarios sharing 3 acts is a coincidence. Wait for **3+ scenarios** with the same block.
- **The block must be a precondition/postcondition, not the focus of any test.** A login-focused test doesn't use a `login_as_X` fragment — login _is_
  the test there, and uses `log_and_screenshot` for the meaningful page transition. The fragment uses plain `log_success` because login-as-setup is
  not a journey frame in callers' context.
- **Unhappy-path tests stay self-contained.** Tests like `failed_logins` or `unauthenticated_*_access` don't use the auth fragment — they must stay
  independent of authenticated state.

## Data-driven tests

When several scenarios share the same flow and only inputs vary, generate them from a dataset. Pattern (mirrors `ocarina-example/.../multi_login.py`
in <https://github.com/mojo-molotov/ocarina-example>):

1. **Dataset** — frozen dataclass + a `Sequence[Case]`. A separate module under `<feature>/datasets/<name>.py` when reused; inline in the scenario
   file when tiny.
2. **Scenario factory** — `_create_<name>_scenario(case: Case) -> SeleniumTestScenario` returns the closure binding the case into the chain.
3. **Test list comprehension** — `<feature>_tests = [create_selenium_test(name=…, test_scenario=_create_…(case)) for case in cases]`.
4. **Suite wiring** — unpack: `tests=[*<feature>_tests, …]`.

### When to use it

- **Same flow shape, varying parameters.** Identical `drive_page` structure differing only in input values is a candidate. Three is a clear win.
- **Don't force it when terminal-step semantics differ a lot.** A dataset works when branches are one conditional act; if every case needs a bespoke
  verification chain, the list comprehension hides more than it expresses.
- **Test names come from the data.** Use a `_test_name(case)` helper or an f-string so the name is meaningful in `pretty_print_results` output.
- **Test names must not contain `/` or `\`.** Ocarina writes the test name as a filename; either slash creates a missing subdirectory and the run
  fails at step 1 with `[Errno 2] No such file or directory`. Use `-` (e.g. `back-forward`, not `back/forward`).
- **Failure cases share the suite, not the structure.** Two failure-mode tests can live in the same suite without sharing a flow shape.

## `SeleniumBackAndForwardNavigationMixin` — shared back/forward navigation

Any POM needing back-button navigation mixes in the framework's
`src/lib/ext/ocarina/adapters/selenium/browser_navigation.SeleniumBackAndForwardNavigationMixin` rather than duplicating the `pre_url` capture +
`driver.back()` / `driver.forward()` + `ec.url_changes` pattern. Place before `SeleniumTitleMixin` in the MRO:

```python
class MyPage(SeleniumBackAndForwardNavigationMixin, SeleniumTitleMixin, POMBase):
    ...
```

`navigate_back()` captures the current URL, calls `driver.back()`, waits with `ec.url_changes(pre_url)`. `navigate_forward()` does the same with
`driver.forward()` but silently swallows `TimeoutException` — a server-side 302 during a prior `back()` may collapse the forward entry; a no-op
forward is not a failure. Both return `Self`.

## Conventions

- **Read the FRD first.** Element IDs, form field order, URL paths come from the FRD (whatever format your project uses).
- **Public-demo SUTs: no env vars / dotenv.** CURA is a public demo; its URL and credentials live in `src/constants/` and are imported. For non-demo
  SUTs, follow your project's secret-handling convention; never bake secrets into source.
- **URLs go in `src/constants/urls.py` as full URLs.** Never inline a URL in a scenario, page, or connector. POMs take a single
  `url: str = <DEFAULT_URL>` parameter, defaulted to the constant. Scenarios construct pages with just `Page(driver=driver)` and pass `url=...` only
  to override. Same rule for shared fixture data (credentials, hardcoded names) — extract to `src/constants/<topic>.py`.
- **Opinionated CLI keys.** Never rename keys read from `SeleniumCliStoreSingleton` (it's `"workers"`, not `"max_workers"`).
- **Log factories, never inline lambdas.** `.failure(log_error("msg"))` / `.success(log_success("msg"))`.
- **`TYPE_CHECKING` guard.** All type-only imports live inside `if TYPE_CHECKING:`, after all runtime imports.
- **`transient_errors`.** Add types here only when they should auto-retry. Deterministic findings (e.g. a `BackForwardCacheExposureError`) never go
  here.
- **No dead connectors.** A connector function must be used in at least one scenario; speculative ones are caught in review.
- **No direct HTTP calls.** The suite tests through the browser. Raw HTTP (`requests`, `httpx`, `curl`) is out of scope unless a direct call is the
  only way to functionally exercise a specific user path (state seeding the UI can't produce). When in doubt: if a real user can do it through a
  browser, do it through a browser.
- **POM encapsulates page mechanics.** Don't expose multi-step UI (`open_nav` then `click_link`) to scenarios. Merge into one POM method (e.g.
  `logout()` opens the nav and clicks the link internally).
- **No FRD references outside `#` comments.** Test names, log messages, exception messages, docstrings — none contain `FRD §x.x` / `JIRA-1234` /
  Confluence anchors. Those references belong in the FRD and in inline comments. The FRD number means nothing to someone reading a test report.

## Hard-won rules

Each rule statement leads. History and forbidden footguns follow only when load-bearing.

### Verify SUT behaviour — don't theorise

When the SUT's source is accessible (open source, or you own it), read it before building on a server-side claim. CURA is open source, so the
worked-example command is:

```bash
gh api repos/katalon-studio/katalon-demo-cura/contents/<file>.php --jq '.content' | base64 -d
```

For other stacks: clone a Node/Java/Go/Ruby/Python/.NET repo; pull individual files via `gh api`; for a closed-source SUT with an API contract, read
the OpenAPI / Protobuf / GraphQL schema instead.

When to read it:

- A test fails on a claim you can't observe from the browser (CSRF mechanics, session lifecycle, redirect logic, validation rules).
- A code comment asserts _"the SUT does X"_ and is load-bearing for a workaround.
- You're about to add a workaround based on what you _think_ the SUT does.

Don't reach for the source for things the browser already tells you (rendered HTML, visible errors, URL changes) or things the FRD already documents.

When a comment asserts a load-bearing behaviour, confirm against the source and cite the file/function inline. If the claim is wrong, fix the test and
the comment in the same change.

**Forbidden as workarounds for hypothesised behaviour:** `driver.delete_all_cookies()`; `driver.refresh()` / `location.reload(true)` to "bypass
cache"; query-string cache-busters (`?_=<ts>`); session-reset rituals (logout-then-relogin) "to refresh the CSRF token"; any browser-state
manipulation a real user wouldn't perform. A real user logs out by clicking logout and logs back in by filling the form — nothing more. If the test
needs more than that to pass, the test is wrong or the SUT is broken; in the second case the test should fail (and document the gap), not paper over
it.

_History:_ a propagated `"CSRF token consumed after first booking"` comment in `ocarina-with-ai-example` seeded multiple such workarounds; the
deployed CURA login form has no CSRF token at all (the PHP source calls `$antiCSRF->insertHiddenToken()` but the deployed app doesn't render the
input). Always verify the claim against the deployed app before propagating the workaround.

### Inspect the SUT for security / spec gaps

This is the **encouraged** use of source inspection (when source is available). CURA is a worked instance — full of gaps that the deployed app shows
but the browser alone can't fully explain:

- No CSRF on deployed forms (source calls `$antiCSRF->insertHiddenToken()`; deployment doesn't render it).
- No server-side input validation on the appointment form (client-side `required` strippable; submit accepted).
- No booking uniqueness check (same facility/date/programme accepted N times).
- History rendered in submission order instead of by visit date.
- `session_destroy()` without cookie expiry on logout.
- `$antiCSRF->isValidRequest()` called against an undefined variable in `appointment.php` (a PHP gotcha — the call returns truthy on an undefined, so
  the check is silently bypassed).

Most are invisible from the browser. The source tells you the difference between a correctly-enforced rule and a coincidence.

Proactively read it when:

- Adding or revising a gap test — read first, then write the test against the _actual_ mechanism so the failure message matches reality.
- A gap test passes when you expected it to fail (or vice versa) — find out whether the SUT, the deployment, or the test scaffolding changed.
- A test comment makes a load-bearing claim about server-side behaviour.
- You spot a bug pattern in one file (e.g. an undefined `$antiCSRF` in `appointment.php`) — grep the rest for the same pattern.

Every gap goes into the gap inventory and, if user-facing, into the FRD's known-bugs section (CURA's are in `CURA_FRD.md` §9). The point is that a
future reviewer doesn't have to re-derive what we already know.

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
never produce. "We tested that CURA accepts a duplicate booking" — fine. "We tested `' OR 1=1 --` in the username field" — not this kind of suite.
Active security testing belongs in Burp / ZAP / sqlmap / a dedicated engagement.

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
- Whenever you suspect a deployment-vs-source discrepancy (the source says X, the live HTML appears to do Y).

A probe is **not** a test (no assertions, not in CI, not parallel-safe), not a long-lived artifact, not something to commit. The output is the
_answer_, not the script — once the answer lands in the gap inventory, the spec doc, a new test, or a source-cited comment, delete the probe.

### Evidence is local — re-derive for every new question

A probe's value is that it removes inference, so it must not _contain_ one — and the same principle extends past the probe itself. A probe's output is
evidence only for what _that_ probe literally did; a prior run's diagnosis is evidence only for _that_ run's failure. Neither extends to a new
question without re-derivation. The trap, in both cases, is reading stale evidence as if it answered the current question.

**For probes — "exact target" means all of: exact locator, exact screen / page state, exact wait condition, exact action.**

- **A locator is half a location — the screen is the other half.** The same selector on two screens is two different targets:
  `By.CSS_SELECTOR, "button[type='submit']"` on the login page ≠ the same on a form page elsewhere.
- **Never infer from a probe written for a different element/screen/use-case.** Real slip: an Enter-on-button probe used `button[type='submit']` while
  the dispatcher it validated used `By.ID, "btn-book-appointment"`. "Probably the same button" is the exact inference the probe existed to kill.
- **Same locator, same screen, same condition, same action.** If the code uses `By.ID, "x"` with `element_to_be_clickable` and `Keys.ENTER`, the probe
  uses the same three. "Close enough" leaves a hole exactly where you needed certainty.
- **One probe, one question, one target.** Reusing a probe for a second target means editing it to the new exact screen/locator/action and re-running
  — not reading the old output.

**For diagnoses across runs — logs, screenshots, and prior comments describe a _past_ failure.** For a _current_ failure, treat them as hypotheses to
test, not conclusions to inherit. Re-derive the cause from this run's evidence (current screenshot, current network response, current source) before
reaching for the previously-tried fix. One extra check is cheap; stacking workarounds on a wrong diagnosis is what ends in a reboot.

### Probe sequences vs ritual workarounds — multi-action "dances"

A scenario sometimes needs a long chain that doesn't map to a single user intent: log in → page A → page B → log out → press back → assert; or submit
→ log out → log back in → submit again → check history. Call any such chain a **dance**. Two kinds, and the difference matters.

**Probe sequence (legitimate).** The dance _is_ the test. Removing any step changes what's being tested. CURA-worked examples:

- `Logout - Session holds under back-forward stress (3 cycles)` — log out, then hammer back/forward against the history page N times; a single
  back-press can miss a cache edge case that only surfaces once the cache has been hit and re-hit.
- `Appointments - Saturation` — 5 sequential bookings _in one session_ probes whether CURA imposes any per-session rate limit. Repetition is the test.
- `History - Empty state on fresh login` → `click 'Go to Homepage'` → `verify homepage` — the click-through is the FRD's specified path (REQ-HIST-4).

**Ritual workaround (not legitimate).** Glue around a _hypothesis_ about SUT behaviour. Symptoms:

- The justifying comment asserts a SUT behaviour ("CSRF token consumed after first submission", "logout doesn't expire the cookie so we must clear
  cookies") that was never verified against the source.
- Removing the step doesn't change _what_ the test exercises, only whether it works.
- The dance touches browser state a real user wouldn't (`delete_all_cookies()`, `location.reload(true)`, query-string cache-busters, manual
  session-cookie expiry).

**When you write a dance,** ask: if a user did exactly this sequence by hand, does each step have a reason from their perspective? Yes → probe
sequence, keep it, document the _concern being probed_ in the scenario docstring. No → stop, read the source, fix the underlying assumption.

The same physical action can be a probe in one test and a workaround in another — intent, not gesture. _logout→relogin as the focus of a
session-integrity probe_ → probe sequence; _logout→relogin between two bookings to "refresh the CSRF token"_ → ritual workaround (removed in
`ocarina-with-ai-example`; the CSRF theory was unsupported by the PHP).

### A cross-browser behavioural difference is a finding, not a test to route around

When a test passes on one browser and fails on another, the divergence **is the result** — that's what the multi-browser matrix exists for. **Never
skip a test on the browser where it fails.**

Investigate which side of the line the failure is on:

- Real user-facing defect → the test is gold; stays red until the app is fixed; finding goes in the FRD / gap inventory.
- Genuine browser/driver interaction defect → document in the gap inventory, keep the test. A red cell that means something beats a green cell that
  lied.
- Test scaffolding that only works on one browser → the one case where you fix the _test_ — but you fix it to work on **both**, never by removing it
  from one.

"Passes everywhere except Chrome" is not a reason to stop running it on Chrome. It is a reason to find out why.

### Functional testing simulates a real human — ask "would a real person hit this?"

Every test here stands in for a person clicking through the SUT (CURA, in the worked example) in a browser. When a test fails — especially on one
browser only — the decisive question is not "why is the automation unhappy?" but: **would a real person, doing exactly this in this browser, hit the
same wall?**

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

**A confirmed BFcache exposure raises a dedicated, non-transient exception** (e.g. `BackForwardCacheExposureError` in `src/lib/errors.py`). Never a
bare `AssertionError`; never a Selenium `WebDriverException`. The finding is deterministic and must never land in `transient_errors` (and so must
never surface as an auto-retried `TimeoutException`). Catch Selenium's `TimeoutException` from the reload-wait and re-raise as the dedicated type. The
exception name in the report _is_ the diagnosis.

BFcache eligibility varies by browser and version — some browsers admit even `no-store` pages to BFcache; others honour `no-store` and re-request.
That divergence is the matrix's job to surface. In `ocarina-with-ai-example`, `HistoryPage.verify_back_button_did_not_restore_view` is the worked
example, split across `post_logout_bfcache_exposure` and `post_logout_server_invalidation`.

### Scenario file structure

**One scenario per file.** Hand-written multi-scenario files are not allowed — split them. The only exception is **data-driven families**, where a
factory generates N tests from a `Sequence[Case]` and lives in one file because the flow is shared and only inputs vary.

**Top docstring gives the flow as arrows.** A reader must know exactly what the file exercises before reading any code. The arrow form
(`open page → fill form → submit → verify confirmation`) is the same mental model as the scenario itself (chained `act()` calls). The docstring also
lists pre/post-fragments and any setup/teardown specific to the file. If a section has none, write `(none)` — explicit "no setup" is information.

```python
"""Submit the primary form and verify the result lands in history.

Flow:
  open form → fill (field1, field2, field3) → submit
  → verify confirmation → open history → verify submitted record matches input

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
    _records = (By.CSS_SELECTOR, ".panel.panel-info")
    _empty_message = (By.XPATH, "//*[normalize-space()='No record.']")
    _btn_go_homepage = (By.XPATH, "//a[normalize-space()='Go to Homepage']")

    def __init__(self, *, driver: WebDriver, url: str = HISTORY_URL) -> None:
        ...
```

### Always use WebDriverWait — never raw find_element

Raw `driver.find_element()` and `find_elements()` snapshot the DOM at call time. If the page is still rendering or running framework initialisation,
the call either raises `NoSuchElementException` or returns a stale element — intermittent and hard to reproduce.

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
spinner hides). When the element never existed (e.g. a section locator on the login page after redirect), Selenium 4 still fires the full implicit
wait on each poll before raising `NoSuchElementException`. Use `ec.url_changes` for redirect checks and `execute_script` querySelectorAll for static
DOM absence.

**Implicit wait is set by the CLI (`--wait-timeout`).** Never read, modify, or work around it in POM/test code — it is framework infrastructure. No
`driver.implicitly_wait(...)` outside the Ocarina driver builder.

**Exception: `find_elements` (plural) for multi-element reads after `verify()`.** When `verify()` has confirmed the section is loaded, subsequent
`find_elements` on child elements of that section is safe (CURA pages are server-rendered, so all children are present when the landmark element is;
same principle for any server-rendered SUT).

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

Worked example: CURA's `txt_visit_date` Bootstrap 3 datepicker — see `AppointmentPage.enter_visit_date` in
<https://github.com/mojo-molotov/ocarina-with-ai-example> for the JS + widget-API call.

### Setup/teardown actions: prefer the URL, save the UI click for the test that owns it

When a feature has a URL-level entry point (a GET that performs the action server-side and returns a known target page) and the same feature is
reachable via a UI element wired through scripted event handlers:

- **Tests where the action is incidental** (pre/post-fragments, intermediate state transitions) use the URL. `driver.get(<action_url>)` is direct, has
  no event-handler dependency, and blocks until the server's redirect lands.
- **Tests where the action is the subject under verification** ("the sidebar link still works", "the submit button still routes correctly") click the
  UI element, because _that path_ is what they assert.

This keeps unrelated tests focused while preserving a dedicated test that owns the UI path and fails loudly if event wiring breaks.

Worked example (in `ocarina-with-ai-example`): `Sidebar.logout()` uses `driver.get(LOGOUT_URL)` because logout is teardown in every test except one;
`Sidebar.logout_via_sidebar()` drives the real `#menu-toggle` → Logout-link click and is used by exactly one test, `logout.py`, which owns that path.

**Watch the justification, not just the split.** CURA's `Sidebar.logout()` originally carried "a jQuery dispatch race that proved unreliable in
headless Chrome" — and that was false. A probe drove the exact sidebar path in clean headless Chrome (password manager off, as
`create_drivers_pool.py` builds it) and it worked 5/5; the "race" was the Chrome password-breach modal swallowing the click, the same misdiagnosis as
the Enter-on-button case (see "Form submission paths"). The URL-for-teardown split is still right — but on its real merit (a direct GET is the most
reliable way to _reach_ a post-action state), never on an invented browser bug. If you write "prefer the URL because the UI path is flaky", prove the
flakiness with a probe first or don't claim it.

### Shared UI components live in `pages/components/`, named for the component

Some UI is not a page — it is chrome rendered on _every_ page (a sidebar, a header, a cookie banner, a global modal). It has no URL, isn't a
navigation target, and parking its actions on one arbitrary page object (or in a vague `commons.py` grab-bag) misleads every reader about where that
behaviour belongs.

Model each such component as its own POM under `src/pages/components/`, **named for the component**, not for its role:

- `pages/components/sidebar.py` → `class Sidebar` ✓
- `pages/components/commons.py`, `pages/components/shared.py`, `pages/components/misc.py` ✗ — "Commons" is not a thing on the screen; `Sidebar` is. A
  grab-bag filename invites a grab-bag class.

One component, one file, one class. A component POM still subclasses `POMBase` (+ `SeleniumTitleMixin`); `verify()` checks the component is present
(in CURA, `Sidebar` verifies `#menu-toggle`). Connectors live in `connectors/test_steps/<component>.py`, mirroring the filename. Worked example:
`Sidebar` in `ocarina-with-ai-example` owning `logout()`, `logout_via_sidebar()`, and the nav-link methods.

### TYPE_CHECKING imports must be verified against the actual module

With `ignore_missing_imports = true` in `pyproject.toml`, mypy will not flag a wrong import path inside an `if TYPE_CHECKING:` block — the name
resolves nominally at type-check time and never runs, so typos and wrong-module references persist silently. Verify any new `TYPE_CHECKING` import
against the actual module's public API rather than copy-pasting from a similar-looking module.

Example: in Ocarina, `ILogger` lives at `ocarina.ports.ilogger`, not at `ocarina.custom_types.logger` (that module does not exist).

### Alias imports that shadow a kwarg or local name

When the same identifier is both a kwarg of a function you call and the name of a function/symbol you import, the import shadows the kwarg in your
module and produces confusing call-site errors. Alias the import under a private name (`_xxx`).

Example: `from ocarina.opinionated.launcher.bootstrap import run_plugins as _run_plugins` because `bootstrap(run_plugins=...)` also accepts a
`run_plugins` kwarg.

### Long string literals — implicit concatenation

When a strict linter enforces a line length (Ruff's default `E501` is 88 chars) and a string literal in `.failure()` / `.success()` would exceed,
split with Python implicit string concatenation — adjacent literals separated by whitespace are joined at compile time:

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

**The hard-won part:** _"`send_keys(Keys.ENTER)` on a `<button>` is unreliable"_ was once treated as fact and propagated into three files in
`ocarina-with-ai-example` — a **misdiagnosis**. The Chrome password-breach modal was silently swallowing _all_ input after a login (clicks included);
"Enter didn't submit" got pinned on the interaction path rather than the modal. A probe later showed Enter-on-button submits 12/12 in a clean browser
(with the password manager disabled per `create_drivers_pool.py`). Before you declare an interaction path unreliable, find out _why_ it failed; a
swallowed input, an intercepting widget, and a genuinely-bad path all look identical from "the form didn't submit."

Which forms expose which dispatchers is per POM and should be documented in the test-strategy doc.

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
"All N submissions recorded" is a lie if the assertion only confirmed one of them (this was a real bug: a saturation test whose check proved "value
appears ≥ once" while its message announced "all 5 recorded"). If you want the message to say "all N", the assertion behind it must verify all N. An
overstated message is worse than no message, because the reader believes it.

### Use the constant — never retype its value

A value bound to a named constant or variable belongs everywhere by that name: in code, in messages, in test names, in fixtures. Retyping the literal
duplicates the source of truth — change the constant, miss one of the copies, and the suite quietly contradicts itself. That is what variables _exist
for_.

_Example:_ a test imports `DEMO_USERNAME` and uses it correctly in `login_with_credentials(DEMO_USERNAME, DEMO_PASSWORD)` and in
`f"Submitted login as {DEMO_USERNAME}"` — but the test name slipped through as `"Valid Login - John Doe"`. Wrong; should be
`f"Valid Login - {DEMO_USERNAME}"`.

The one exception is the constant's own definition (`DEMO_USERNAME = "John Doe"` — by definition the literal lives there). Everywhere else
interpolates. If you find yourself typing a value that already has a name in scope (or one easily added to `src/constants/`), use the name — or add
one.

### Datasets are authoring decisions — stop and ask before running

A test dataset is not implementation detail. It is a deliberate authoring decision about _what_ to exercise: which input, which date, which
credentials, which combination of fields, which edge values. Those choices belong to the user, not to whoever happens to be typing.

**When you create or modify a dataset, do not run the tests automatically.** Stop, report what you added or changed ("I built these cases: X, Y, Z; I
changed Q from A to B"), and wait for the user to review and approve — _then_ run. This applies to anything that is meaningfully _test input_:

- explicit case tuples (dataset rows, inline failure-case lists),
- lists of values used as test data (date matrices, batch inputs),
- module-level constants used as test inputs (named values, comments embedded in submissions),
- new credentials or usernames.

Mechanical refactors that don't change the data (renaming a field, reordering, restyling) don't trigger this — only changes to _what is being tested_.
When in doubt, treat it as a dataset change and ask.

A silent dataset choice plus a green run looks like "I ran the tests successfully" while quietly imposing the author's idea of coverage on the user.
Stopping surfaces the decision.

### Strict linter conventions

When a project enables a strict ruleset like Ruff's `select = ["ALL"]`, a few rules come up a lot. Know them so you can read suppressions and write
clean code:

- `TC002` / `TC003` — runtime imports must not be in `TYPE_CHECKING` blocks.
- `S105` — hardcoded passwords flagged; suppress with `# noqa: S105` on credential constants.
- `D401` — docstrings in imperative mood ("Build…" not "Builds…").
- `ANN` — return type annotations required on public functions.

## Dev setup and quality checks

Both are walked by the `setup-environment` skill (venv, dev tooling, `CLAUDE.local.md` paths, the `ruff` / `mypy` / `pre-commit` quality loop, and a
smoke-check of the runner). Run that skill on first checkout or after any change that would alter `pip install` resolution. The quality loop —
`ruff format src/` then `ruff check src/` then `mypy src/` then `pre-commit run --all-files --config .pre-commit-config.yaml` — runs before every
commit and must match what CI runs.

## CI workflows

Two workflows are conventional:

| Workflow     | Trigger             | What it does                                                                                |
| ------------ | ------------------- | ------------------------------------------------------------------------------------------- |
| `<name>_ci`  | every PR            | Lint + typecheck (`ruff format` check, `ruff check`, `mypy`). Fast; gates merges.           |
| `<name>_e2e` | manual or scheduled | Full cycle on a multi-browser matrix, `fail-fast: false`, `--workers N`, uploads artifacts. |

The e2e matrix uses `fail-fast: false` — a Firefox failure doesn't abort Chrome. **Never collapse the matrix to a single browser** to "simplify" a
run; browser-specific back-navigation (BFcache, session) is exactly what the matrix catches. Both jobs must pass before calling the suite green.

If e2e is manual, it doesn't gate merges — it's explicit and expensive. To require it on a PR, dispatch from the branch and link the run in the PR
description.

## PR descriptions

Two required sections, every PR:

- **`## Summary`** — what changed and why, one short paragraph. Lead with the rule or pattern you applied, not the file list.
- **`## Test plan`** — checklist. `[x]` what you ran locally (`ruff format && ruff check && mypy`, full e2e cycle); `[ ]` what only the manual e2e
  workflow can confirm (artifact upload, cross-browser parity, fresh DOCX render). State the local result: `All N tests pass locally (X.Xs)`. The PR
  gate runs `lint-and-typecheck` only, so this is the sole functional signal until someone dispatches the e2e workflow.

### Hierarchy slice (when test boundaries shift)

Ocarina's `Cycle → Campaign → Suite → Test` hierarchy makes impact legible in two lines. When a PR adds, removes, relocates, or renames anything in
that hierarchy — including moving a test in or out of the smoke gate — render the affected slice as a tree under the Summary:

    Smoke (fail-fast gate):
      Prerequisites
        └─ Authentication baseline       (valid_login)

    Main:
      Authentication
        ├─ Session management             (logout)
        └─ Failure modes                  (failed_logins + unauthenticated_access)
      Submissions
        ├─ Happy paths                    (submission_tests, data-driven)
        └─ History                        (view_history)
      User journeys
        └─ Cross-feature flows            (submit_and_verify_history)

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
