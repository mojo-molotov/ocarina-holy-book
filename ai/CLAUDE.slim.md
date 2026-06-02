# Ocarina Test Suite — Claude Context (slim)

This is the **hot-context** version of `CLAUDE.md` — the rules that constrain action on every turn, stripped of the descriptive material (project
layout, hierarchy, naming conventions, CI workflow shape, PR template). Load this when your context window is already heavy with code, logs, or FRD
content; load the full `CLAUDE.md` for onboarding, review tasks, anything that asks _"how is this project shaped?"_.

When the slim file and the full file disagree, the full file wins — this is a condensation, not a fork. If a rule here feels incomplete, open the full
file at the matching section name. **Driver-level mechanics (the wait API, selector form, submission primitives, navigation, CLI flags) are
adapter-specific and live in `CLAUDE.selenium.md` / `CLAUDE.playwright.md`.** The rules below state the adapter-neutral principle; open the appendix
for the adapter on your `CLAUDE.local.md` line for the concrete form.

These rules assume **maximum latitude** (open-source SUT, live probing, public creds, web research — the CURA demo). When the engagement is narrower,
a `CLAUDE.profile.md` appendix (from `profile-environment`) **tightens** them — it may forbid source-reading, live probing, web egress, or unredacted
screenshots. The profile only ever tightens, never loosens; when present it is the final word.

## Philosophy

- **No tricks or hacks.** JS-clicks to skip hit-testing, lint suppressions to silence a rule, `time.sleep` to mask a race, `driver.implicitly_wait` to
  patch a timing bug. If a hack is genuinely the only option, document why no clean fix exists and mark it so a reader doesn't copy the pattern.
- **Teach the pattern, not the symptom.** A rule reads as reusable knowledge, never a log of which browser, version, or POM showed the problem first.

## Evidence and verification

- **Verify SUT behaviour — don't theorise.** Read the source (open-source repos via `gh api`; OpenAPI / Protobuf / GraphQL schema for closed-source)
  before building on a server-side claim. The browser is authoritative for rendered HTML, visible errors, URL changes; the source is authoritative for
  redirects, session lifecycle, CSRF mechanics, validation rules.
- **Forbidden workarounds for hypothesised behaviour:** `driver.delete_all_cookies()`; `driver.refresh()` / `location.reload(true)` to "bypass cache";
  query-string cache-busters (`?_=<ts>`); session-reset rituals (logout-then-relogin) "to refresh the CSRF token"; any browser-state manipulation a
  real user wouldn't perform.
- **Evidence is local — re-derive for every new question.** A probe's output is evidence only for what _that_ probe literally did (exact locator,
  exact screen, exact wait, exact action — one probe, one question, one target). A prior run's diagnosis is evidence only for _that_ run's failure;
  treat it as a hypothesis to retest, not a conclusion to inherit. Stacking workarounds on a wrong diagnosis is what ends in a reboot.

## Security testing — functional and static, never active

- Static analysis of the SUT source for spec/security gaps: **encouraged.**
- Functional tests through the normal UI/HTTP path that exercise security-relevant behaviour: **fine.**
- **Forbidden, no exceptions:** crafted attack payloads (SQLi, XSS, command injection, path traversal, deserialisation), token tampering, signature
  stripping, cookie forgery, session-fixation, cross-origin POSTs constructed outside the suite, directory enumeration, DOS, rate-floods. Anything
  that escalates from "use the app like a user" to "attack the app like an adversary" belongs in Burp / ZAP / sqlmap, not this suite.
- **This line is invariant** — a `CLAUDE.profile.md` can only narrow it (e.g. functional security tests out of scope too); no engagement "allows"
  active testing here. That's a different engagement entirely.

## Cross-browser

- **A cross-browser behavioural difference is a finding, not a test to route around.** Never skip a test on the browser where it fails. Real defect →
  keep red, document. Driver/browser interaction defect → keep red, document in gap inventory. Test scaffolding that only works on one browser → fix
  the test to work on **both**, never by removing it from one.
- **Never `--workers 1`.** Single-worker runs mask concurrency failures and diverge from CI. Match CI's worker count.

## Driver / POM discipline

- **Always wait for an element to be ready — never read the DOM raw.** Adapter-neutral principle; the wait API is adapter-specific → appendix.
  - **Selenium** → explicit `WebDriverWait` + expected condition (clickable / visible / present / invisible / `url_changes` / `execute_script`
    querySelectorAll); implicit wait is CLI-set (never `driver.implicitly_wait(...)` in POM/test code); `find_elements` plural after `verify()` is the
    one exception. Full table in `CLAUDE.selenium.md`.
  - **Playwright** → locators auto-wait per action with an explicit `timeout`; no implicit wait, no condition table; race two outcomes rather than
    blocking the whole budget on a present-element `wait_for(state="hidden")`. See `CLAUDE.playwright.md`.
- **Not an exception:** "this page is static / already loaded" — don't reason your way past the rule.
- **Widget-decorated inputs (datepicker, autocomplete, masked-input):** drive the widget's own affordance/API, don't fight its intercepts. Fill the
  widget-backed field _last_ or close it before the next field. (Concrete form → appendix.)
- **POM selectors live at the top.** One block — Selenium `By.*` tuples at class top, Playwright string locators at the top of `__init__`.
- **POM encapsulates page mechanics.** Don't expose multi-step UI (`open_nav` then `click_link`) to scenarios — merge into one POM method.

## Scenario / test discipline

- **One scenario per file.** Exception: data-driven families (factory + `Sequence[Case]`).
- **Top docstring gives the flow as arrows**, lists pre/post-fragments. Write `(none)` when empty.
- **All the adapter's `create_*_test()` at the bottom** (`create_selenium_test` / `create_playwright_test`), grouped. Never interleave scenario → test
  → scenario → test.
- **Log factories, never inline lambdas.** `.failure(log_error("msg"))` / `.success(log_success("msg"))`.
- **Every `drive_page` produces at least one `log_and_screenshot`** on the act that shows the resulting state. Pre/post fragments use plain
  `log_success`. No manual failure shots (the `autoscreen_on_fail=True` burst handles it).
- **A message must never claim more than its `act` verified.** "All N submissions recorded" is a lie if the assertion only confirmed one.
- **No magic numbers in code; never in log/success/error/screenshot messages.** Interpolate named constants if a quantity must appear; usually the
  log's own line count speaks for itself.
- **Use the constant — never retype its value.** Test names, log messages, fixtures all reference the constant by name. The constant's own definition
  is the only literal.
- **No FRD references outside `#` comments.** Test names, log messages, exception messages, docstrings — none contain `FRD §x.x` / `JIRA-1234`.

## Datasets

- **Datasets are authoring decisions — stop and ask before running.** When you create or modify a dataset (explicit case tuples, value lists used as
  test data, module-level constants used as inputs, new credentials), report what changed and wait for sign-off before running. Mechanical refactors
  (renames, reordering) don't trigger this; only changes to _what is being tested_ do.
- **Test names must not contain `/` or `\`.** Ocarina writes the test name as a filename; either slash creates a missing subdirectory and the run
  fails at step 1 with `[Errno 2] No such file or directory`. Use `-` instead.

## Reasoning about failure

- **Functional testing simulates a real human.** When a test fails — especially on one browser only — ask: would a real person, doing exactly this in
  this browser, hit the same wall? Yes → real defect. No (only synthetic automation affected) → tool artifact, fix in test/POM.
- **Escalate from synthetic toward real to find the boundary, empirically — _how_ is adapter-specific.** Selenium has a real gap to walk (`.click()` →
  re-find → keyboard → ActionChains → CDP); Playwright dispatches trusted input by default, so it collapses to actionability. → appendix. Don't
  conclude by reasoning.
- **Probe sequence vs ritual workaround — the "dance" test.** If a user did exactly this sequence by hand, does each step have a reason from their
  perspective? Yes → probe sequence (keep, document the concern being probed). No → stop, read the source, fix the underlying assumption.

## BFcache exposure — the `back()` → `refresh()` check

A page from the browser's back-forward cache is restored locally with no server round-trip; any server-side access control never runs. If `back()` did
not redirect away but `refresh()` does, `back()` served a BFcache snapshot. If `refresh()` also fails to redirect, the server itself isn't
invalidating — a worse, separate finding. Two outcomes, two distinct failure messages.

This is the one place a programmatic reload is legitimate — it _is_ the instrument of the assertion (Selenium `driver.refresh()` / Playwright
`page.reload()` → appendix). A confirmed BFcache exposure raises a dedicated non-transient exception (e.g. `BackForwardCacheExposureError`), never a
bare `AssertionError` or a raw driver exception. Must never land in `transient_errors`.

## Setup / teardown

- **Action with both a URL-level entry point and a UI element:** tests where the action is incidental → use the URL (`driver.get(<action_url>)`).
  Tests where the action is the subject under verification → click the UI element, because _that path_ is what they assert.

## When to extract a fragment

- **Don't extract preemptively.** Wait for **3+ scenarios** with the same block.
- The block must be a **precondition/postcondition, not the focus** of any test.
- **Unhappy-path tests stay self-contained** — `failed_logins`, `unauthenticated_*_access` don't use the auth fragment.
