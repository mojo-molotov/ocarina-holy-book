# Ocarina Test Suite — Playwright adapter appendix

Driver-level rules for a suite wired on **Ocarina's Playwright adapter** (shipped since Ocarina v1.1.3). `CLAUDE.md` holds the framework-neutral rules
(hierarchy, scenarios, reports, philosophy, the hard-won _principles_); this file holds the Playwright-specific _mechanics_ those principles resolve
to. When a rule here and a principle in `CLAUDE.md` disagree, the principle wins — this is the Playwright realisation of it, not a fork.

Use this appendix when `CLAUDE.local.md` records the adapter as `playwright`. The Selenium realisation of the same principles is in
`CLAUDE.selenium.md`. The worked example for this adapter is <https://github.com/mojo-molotov/ocarina-with-playwright> (the "Igoristan" SUT). Verify
any symbol below against the installed Ocarina or that clone before relying on it — see `understand-ocarina`.

## Adapter surface (names this adapter binds)

The framework-neutral text in `CLAUDE.md` says "the adapter's `create_*_test`", "the adapter's CLI store", etc. For Playwright those are:

| Concern          | Playwright symbol                                                                                                                         |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Test factory     | `create_playwright_test(name=…, test_scenario=…, post_test_scenarios_fragments=…)` — `ocarina.dsl.testing.playwright.create_test`         |
| Watcher factory  | `create_playwright_watcher`                                                                                                               |
| Scenario type    | `PlaywrightTestScenario` (`Scenario(test_chain=…)` from `ocarina.custom_types.scenario`)                                                  |
| Driver / pool    | `PlaywrightDriver` (`ocarina.infra.playwright.driver`), `create_playwright_drivers_pool` (`ocarina.infra.playwright.create_drivers_pool`) |
| CLI store        | `PlaywrightCliStoreSingleton`, `create_playwright_auto_cli_store` (`ocarina.opinionated.cli.playwright.*`)                                |
| POM mixin / base | `PlaywrightTitleMixin` (`ocarina.infra.playwright.mixins`), `POMBase` (`ocarina.pom.base`)                                                |

A POM subclasses `POMBase` plus `PlaywrightTitleMixin` and stores a `PlaywrightDriver` on `self._driver`:

```python
@final
class DashboardLoginPage(PlaywrightTitleMixin, POMBase):
    def __init__(self, *, driver: PlaywrightDriver, url: str = DASHBOARD_URL) -> None:
        self._driver = driver
        ...
```

## The driving model — everything goes through `driver.submit(lambda page: …)`

This is the one big difference from Selenium and it shapes every POM method. Playwright's **synchronous API binds its objects to one thread**, so the
`PlaywrightDriver` marshals all Playwright calls onto a dedicated owner thread. Page objects never touch a `page` directly; they hand a thunk to
`driver.submit`, which runs it on the owner thread and returns the result:

```python
def _click(self, selector: str, timeout: float) -> None:
    self._driver.submit(
        lambda page: page.locator(selector).first.click(timeout=int(timeout * 1000))
    )

def _fill(self, selector: str, value: str, timeout: float) -> None:
    self._driver.submit(
        lambda page: page.locator(selector).first.fill(value, timeout=int(timeout * 1000))
    )

def open(self) -> Self:
    self._driver.submit(lambda page: page.goto(self._URL))
    return self
```

Reads come back through `submit` too: `current_url = self._driver.submit(lambda page: page.url)`. Never stash a `page`, `Locator`, or `ElementHandle`
on `self` and use it later off-thread — marshal each interaction.

## Waiting — locators auto-wait; there is no implicit wait

Playwright has **no implicit wait**. Locator actions (`click`, `fill`, `press`, `check`) auto-wait for the element to be actionable up to the supplied
`timeout`; you don't assemble an expected-condition before each action the way Selenium does. So there is **no `WebDriverWait` table here** — the
discipline is different:

- **Pass an explicit `timeout` to every action** (the suite's `get_timeout()` in milliseconds). Don't rely on Playwright's 30 s default; honour the
  CLI `--wait-timeout`.
- **For an explicit settle, use a locator wait or a function wait**, marshalled:
  - element appears → `page.locator(sel).first.wait_for(state="visible", timeout=…)`
  - element leaves → `wait_for(state="hidden", …)` (the suite wraps these as `wait_for_hidden`, `wait_for_h1_contains`, `wait_for_title_contains`)
  - a custom condition / racing two outcomes → `page.wait_for_function(js, timeout=…)`
  - assertions → Playwright's `expect(locator)` web-first assertions auto-retry until timeout.
- **The implicit-wait footgun is reversed.** Selenium's drag was the implicit wait firing on every miss; Playwright's is a `wait_for(state="hidden")`
  on an element that is _still present_ blocking the **whole** timeout budget before a retry loop can turn over. When you have two possible outcomes
  (success unmounts a field, failure surfaces an error and leaves it), wait for **whichever settles first** with `wait_for_function`, and return on
  failure immediately — don't wait out the budget on the field that isn't going to move. (Worked: `DashboardLoginPage._login_submit_succeeded`.)
- **`find_elements` plural exception (Selenium) has no analogue** — Playwright `locator` is lazy and re-queries on each action, so the staleness the
  Selenium rule guards against doesn't arise. Use `locator.all()` / `locator.count()` (marshalled) for multi-element reads.

## POM selectors live at the top — string locators

Same _principle_ as `CLAUDE.md` ("a POM's selectors are its contract with the DOM; keep them in one block"), different _form_: Playwright selectors
are plain strings, declared together at the top of `__init__` (a `PlaywrightDriver` is required to build a `Locator`, so they live in the constructor,
not as class-level attributes the way Selenium's `By.*` tuples do):

```python
def __init__(self, *, driver: PlaywrightDriver, url: str = DASHBOARD_URL) -> None:
    self._driver = driver
    self._URL = url
    self._username_input = "#username"
    self._password_input = "#password"  # noqa: S105 — CSS selector, not a secret
    self._login_btn = '[data-testid="login-btn"]'
    self._invalid_credentials_msg = "xpath=//*[contains(text(), 'Invalid credentials.')]"
```

Prefer CSS / `data-testid` selectors; use Playwright's `xpath=…` prefix when XPath is genuinely needed. `get_by_role` / `get_by_text` locators are
also fine — keep them in the same block.

## Form submission paths — locator actions

The dispatcher pattern is identical to Selenium's (a `dict[str, Effect]` of legitimate submission paths, one chosen at random per call — see
`review-submit-dispatchers`); only the primitives change. The Playwright paths:

- `page.locator(submit_btn).first.click()` — click the submit control.
- `page.locator(text_input).first.press("Enter")` — HTML implicit submission from a focused input.
- `page.locator(submit_btn).first.press("Enter")` — Enter on a focused submit button.

```python
self._login_without_otp_action_dispatchers: dict[str, Effect] = {
    "focus_username_input_then_press_enter": lambda: self._press_enter(self._username_input, timeout),
    "click_login_button": lambda: self._click(self._login_btn, timeout),
    "focus_login_button_then_press_enter": lambda: self._press_enter(self._login_btn, timeout),
}
```

Use `fill()` to set field values (it **replaces** the field content — no `clear()` dance; contrast Selenium `send_keys`, which appends). A widget that
intercepts Enter is still a real caveat — drive its API rather than fighting it (see below).

## Trusted input by default — the synthetic→real ladder mostly collapses

`CLAUDE.md`'s principle stands: when a test fails, ask whether a real person would hit the same wall (real defect) or only the automation path is
affected (tool artifact). But Playwright's locator actions dispatch **trusted** input events at the actionable element, so the Selenium synthetic→real
escalation ladder (`.click()` → re-find → ActionChains → CDP) has no Playwright equivalent — there is no "synthetic vs trusted" gap to walk. When a
Playwright interaction "doesn't work", the cause is almost always **the element wasn't actionable** (covered, detached, not yet rendered, animating)
or a **real defect** — not the input being synthetic. Investigate actionability (`locator.wait_for`, an `expect` assertion, a
`page.wait_for_function`) and read the source; don't reach for a CDP trusted-click, you already have one.

## Widget-decorated inputs — drive the widget's API (Playwright form)

Principle in `CLAUDE.md`. Playwright realisation: prefer the widget's own affordance through a locator (`page.locator(label).check()` / `.click()`),
and toggle idempotently — read state first, act only if needed:

```python
if not self._is_otp_checkbox_checked():           # page.locator(cb).is_checked()
    self._click(self._use_otp_checkbox_label, timeout)
```

When a widget visually hides the real input (a styled checkbox driven by its `<label>`), target the label, and `wait_for(state="visible")` it before
acting. Fall back to setting value via `page.evaluate` only when no locator affordance works. Fill the widget-backed field _last_, or dismiss the
widget overlay before the next field — same corollary as Selenium.

## Back/forward navigation

`CLAUDE.md` → "Shared back/forward navigation" says don't hand-roll the dance per POM. On Playwright, back/forward go through the marshalled page:
`driver.submit(lambda page: page.go_back())` / `page.go_forward()`, each followed by a `wait_for_url(...)` / `wait_for_function` settle so the
assertion doesn't race the navigation. Selenium ships `SeleniumBackAndForwardNavigationMixin` for this; **confirm whether the Playwright adapter ships
an equivalent mixin before hand-rolling** (`understand-ocarina` against the installed Ocarina). If none ships, extract one shared helper rather than
copying the capture-URL + back + wait sequence into every POM. (The `ocarina-with-playwright` example reaches its "back to Igoristan" target by
clicking the in-page link, not the browser back-button — a link click is a normal navigation, not the back/forward dance this rule is about.)

## BFcache check — the reload instrument is `page.reload()`

The full BFcache `back()` → reload rule and the dedicated `BackForwardCacheExposureError` are in `CLAUDE.md` (adapter-independent). Back/forward
navigation is `driver.submit(lambda page: page.go_back())` / `page.go_forward()`; the reload that forces a server round-trip is
`driver.submit(lambda page: page.reload())`. Catch Playwright's `TimeoutError`
(`from playwright.sync_api import TimeoutError as PlaywrightTimeoutError`) from the post-reload URL wait and re-raise as the dedicated type. (Selenium
uses `driver.refresh()`; see `CLAUDE.selenium.md`.)

## Running tests — Playwright flags

```bash
python -u src/main.py \
  --browser chromium \
  --workers 3 \
  --wait-timeout 10 \
  --logger terminal+file
```

The neutral flags (`--workers`, `--wait-timeout`, `--logger`, `--only`/`--exclude`, `--not-headless`, `--profile-path`) are in `CLAUDE.md` → "Running
tests". Playwright-specific:

| Flag          | Purpose                                                                           |
| ------------- | --------------------------------------------------------------------------------- |
| `--browser`   | `chromium` / `firefox` / `webkit`                                                 |
| `--video-dir` | Optional: record a session video per driver                                       |
| `--trace-dir` | Optional: write a `trace_<id>.zip` per driver (open with `playwright show-trace`) |

There is **no `--driver-path`** — Playwright manages its own browser binaries (`playwright install`). `--video-dir` / `--trace-dir` replace it as the
adapter's artefact flags. Headless is the default; `--not-headless` shows the UI.

## `CLAUDE.local.md` — Playwright per-machine config

The adapter line is `playwright`. It consumes **no driver path**. Record instead:

- The Playwright browser channel(s) installed (`chromium` / `firefox` / `webkit`) and how (`playwright install`, or the project's
  `make playwright-install`).
- The `~/Library/Caches/ms-playwright/...` browser cache directory only if it is non-default (`PLAYWRIGHT_BROWSERS_PATH` overridden).
- Default artefact dirs for `--video-dir` / `--trace-dir` if the contributor wants them on by default locally.
