# Ocarina Test Suite — Selenium adapter appendix

Driver-level rules for a suite wired on **Ocarina's Selenium adapter**. `CLAUDE.md` holds the framework-neutral rules (hierarchy, scenarios, reports,
philosophy, the hard-won _principles_); this file holds the Selenium-specific _mechanics_ those principles resolve to. When a rule here and a
principle in `CLAUDE.md` disagree, the principle wins — this is the Selenium realisation of it, not a fork.

Use this appendix when `CLAUDE.local.md` records the adapter as `selenium`. The Playwright realisation of the same principles is in
`CLAUDE.playwright.md`. The worked examples for this adapter are `ocarina-example` and `ocarina-with-ai-example` (CURA Healthcare SUT).

## Adapter surface (names this adapter binds)

The framework-neutral text in `CLAUDE.md` says "the adapter's `create_*_test`", "the adapter's CLI store", etc. For Selenium those are:

| Concern       | Selenium symbol                                                                                                  |
| ------------- | ---------------------------------------------------------------------------------------------------------------- |
| Test factory  | `create_selenium_test(name=…, test_scenario=…, pre_test_scenarios_fragments=…, post_test_scenarios_fragments=…)` |
| Scenario type | `SeleniumTestScenario`                                                                                           |
| Driver / pool | `create_selenium_driver`, `create_selenium_drivers_pool`, `SeleniumWebDriversPool`, `BuiltSeleniumWebDriver`     |
| CLI store     | `SeleniumCliStoreSingleton`, `create_selenium_auto_cli_store`                                                    |
| POM mixins    | `SeleniumTitleMixin`, `SeleniumBackAndForwardNavigationMixin`                                                    |
| Browser enum  | `SupportedSeleniumBrowser`                                                                                       |

A POM subclasses `POMBase` (framework-neutral) plus the Selenium mixins it needs, and stores a `WebDriver` on `self._driver`.

## Running tests — Selenium flags

```bash
python -u src/main.py \
  --driver-path <path/to/chromedriver> \
  --browser chrome \
  --workers 3 \
  --wait-timeout 10 \
  --logger terminal+file
```

The neutral flags (`--workers`, `--wait-timeout`, `--logger`, `--only`/`--exclude`, `--not-headless`, `--profile-path`) are documented in `CLAUDE.md`
→ "Running tests". The Selenium-specific ones:

| Flag            | Purpose                                                             |
| --------------- | ------------------------------------------------------------------- |
| `--browser`     | `chrome` / `firefox` always; `edge` on Windows; `safari` on macOS   |
| `--driver-path` | Path to the matching driver binary (chromedriver / geckodriver / …) |

`--wait-timeout` sets the Selenium **implicit wait** — framework infrastructure (see below). `python src/main.py`, not `python -m src.main` (the
neutral rule in `CLAUDE.md` applies unchanged).

## `CLAUDE.local.md` — Selenium driver paths

The adapter line is `selenium`. The per-machine paths it consumes:

- **chromedriver** path — `find ~/ -name chromedriver -type f 2>/dev/null` locates it on Unix-likes. Add geckodriver / msedgedriver only when the
  suite is run against those browsers locally.

## Always use `WebDriverWait` — never raw `find_element`

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

## POM selectors live at the top of the class — `By.*` tuples

All locator tuples (`_xxx = (By.ID, "...")`, etc.) belong in one block at the top of the POM class, immediately after the docstring and before
`__init__`. No locators declared further down next to the method that uses them.

```python
@final
class HistoryPage(SeleniumBackAndForwardNavigationMixin, SeleniumTitleMixin, POMBase):
    """..."""

    _section = (By.ID, "history")
    _records = (By.CSS_SELECTOR, ".panel.panel-info")
    _empty_message = (By.XPATH, "//*[normalize-space()='No record.']")
    _btn_go_homepage = (By.XPATH, "//a[normalize-space()='Go to Homepage']")

    def __init__(self, *, driver: WebDriver, url: str = HISTORY_URL) -> None:
        ...
```

(The framework-neutral _principle_ — "a POM's selectors are its contract with the DOM; keep them in one block" — is in `CLAUDE.md`. This is the
Selenium _form_ of it: `By.*` tuples at class top. Playwright keeps the same principle with string locators; see `CLAUDE.playwright.md`.)

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

## Form submission paths — and verifying _why_ one "doesn't work"

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

## Functional testing simulates a real human — the synthetic→real escalation ladder

The framework-neutral question is in `CLAUDE.md`: when a test fails (especially on one browser only), would a real person doing exactly this hit the
same wall? Yes → real defect. No (only the synthetic automation path is affected) → tool artifact, fix in the test/POM.

For Selenium, answer it **empirically** by escalating from synthetic toward real and watching where it starts working:

    synthetic `.click()` → fresh re-find → keyboard submit → ActionChains move-and-click → CDP trusted input event

The boundary tells you the side of the line. Don't conclude by reasoning. (Selenium's `.click()` is synthetic; Playwright issues trusted input by
default, so this ladder is Selenium-specific — see `CLAUDE.playwright.md` for the Playwright stance.)

## Widget-decorated inputs — drive the widget's API (Selenium form)

The principle (drive the widget's scripting API, don't fight its intercepts; fill the widget-backed field _last_) is in `CLAUDE.md`. The Selenium
realisation: set the underlying field value via `execute_script`, then call the widget's update/hide hook so the widget reflects the new state. The
form sees a normal `<input value="...">` on submit.

Worked example: CURA's `txt_visit_date` Bootstrap 3 datepicker — see `AppointmentPage.enter_visit_date` in
<https://github.com/mojo-molotov/ocarina-with-ai-example> for the JS + widget-API call.

## BFcache check — the reload instrument is `driver.refresh()`

The full BFcache `back()` → reload rule is in `CLAUDE.md` (framework-neutral; the diagnosis logic and the dedicated `BackForwardCacheExposureError`
are adapter-independent). The Selenium instrument of the assertion is `driver.refresh()`. Catch Selenium's `TimeoutException` from the reload-wait
(`ec.url_changes`) and re-raise as the dedicated type. (Playwright uses `page.reload()`; see `CLAUDE.playwright.md`.)
