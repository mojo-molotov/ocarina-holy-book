---
name: write-a-probe
description: Author a one-off **probe** — a throwaway Python script that drives the browser through a suspect flow with whichever instrument fits the question (Selenium, raw HTTP, Chrome DevTools Protocol, or Playwright for reactive SPAs) and prints concrete runtime state (URL, page title, rendered DOM, hidden inputs, cookies, XHR/fetch traffic, timing) so you can see what the SUT actually does before encoding it as a test or accepting a claim about it. Probes bypass Ocarina entirely (no `create_selenium_test`, no suites, no assertions), live in a gitignored directory (`<gitignored>/`), are never committed, and are deleted once the finding lands in a durable artifact (a test, a source-cited comment, the gap inventory, the FRD). Use whenever the user asks to probe a flow, verify a behaviour empirically, capture rendered HTML, observe a redirect chain, inspect SPA network calls, measure inter-request timing, confirm a deployment-vs-source discrepancy, or settle a "does the SUT actually do X?" question. The hard rule for any probe that **reproduces** a production interaction path: exercise the **exact** locator, screen, wait condition, and action the production code uses — never an "equivalent". Observation probes pick the best instrument for the concern.
---

# Write a probe — experiment on the app before formalising

A **probe** is a one-off Python script for empirical investigation: drive the browser (or HTTP) through a suspect flow, print runtime state, settle a
question. It is not a test, it is not part of the suite, it is not parallel-safe, it does not assert. It runs _once_ or _a handful of times_, you read
the output, you write down the finding, you delete the script.

This skill walks the probe-authoring workflow. It complements `CLAUDE.md` → "Throwaway probes" (when to reach for one) and "A probe must exercise the
exact target" (how to write one) — this skill is the _workflow_ that ties them together.

## Where probes live

`<gitignored>/probe_<topic>.py` at the repo root. The directory is gitignored. Probes are never committed and never pushed.

If `<gitignored>/` doesn't exist, create it. If `.gitignore` doesn't already cover it, add the line and stop to flag it — that's a repo-shape change,
not a probe action.

## Pick the tool for the question

Selenium is the default — the production suite is Selenium, and any probe that **reproduces a production interaction path** must use it (the
exact-target rule binds to the production engine). A probe that **observes** rather than reproduces is free to use whatever sees the answer most
directly. Match the instrument to the concern:

| The question is about…                                                         | Instrument                                                                   |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| A production interaction path — does this `.click()` / `Keys.ENTER` step work? | **Selenium**, exact production locator + wait + action (Templates A / C / D) |
| Server response — status, headers, `Set-Cookie`, the redirect chain            | **Raw HTTP** — `httpx` / `requests` / `curl -v` (Template E)                 |
| Does element X render on a reactive SPA, and with what content                 | **Selenium + `WebDriverWait`** (mirror prod) or **Playwright** (Template F)  |
| XHR/fetch traffic — order, payloads, timing, a client-side route change        | **CDP Network domain** or **Playwright** `page.on("response")` (Template F)  |
| When an SPA page is actually settled                                           | **Playwright** `wait_for_load_state("networkidle")` or a content marker      |
| JS console errors / uncaught exceptions during a flow                          | **CDP** Runtime/Log or **Playwright** `page.on("console" / "pageerror")`     |

Selenium 4 itself speaks CDP (`driver.execute_cdp_cmd(...)`), so a Selenium interaction probe that also needs a header override or a quick network
peek doesn't always need a second engine — but when network or timing observation is the _whole point_, Playwright is cleaner. Puppeteer covers the
same ground; Playwright is preferred here for its first-class Python binding that drops into the repo's venv. Whatever the engine, name it in the
probe docstring so the next reader re-verifies with the same instrument.

## The workflow

### Step 1 — One-sentence question

"Does the SUT's `/history` endpoint actually return `Cache-Control: no-store` headers on a logged-out GET?" Or "Does Chrome restore the history page
from BFcache after `back()` post-logout — deterministically?" Or "Is the `LoginPage._btn_login` selector still `button[type='submit']` on the deployed
app?"

If the question takes more than one sentence to phrase, split it into multiple probes.

### Step 2 — Define the exact target

List **all four** dimensions explicitly:

| Dimension               | What it means                                                                                                                                            |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Locator**             | The exact `By.X, "..."` the production code uses. Not an equivalent.                                                                                     |
| **Screen / page state** | The exact page (login, form, history, post-logout homepage, etc.) and the exact state (authenticated / logged out / post-back-navigation / post-reload). |
| **Wait condition**      | What the production code waits on (`element_to_be_clickable`, `presence_of_element_located`, `url_changes`, etc.).                                       |
| **Action**              | What the production code does (`.click()`, `.send_keys(Keys.ENTER)`, `driver.back()`, `driver.refresh()`, `driver.get(...)`).                            |

If the production code reads from a constant (`HISTORY_URL`, `LOGIN_URL`, demo credentials), import the same constants — don't copy the string. The
probe diverging from the constants is exactly the "close enough" trap the rule exists to kill.

### Step 3 — Pick the browser shape

For Chrome, **mirror your project's `create_drivers_pool.py`** — disable the consumer password manager, otherwise post-login probes hit the breach
modal and the result is the modal's behaviour, not the SUT's:

```python
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--window-size=1400,900")
opts.add_experimental_option(
    "prefs",
    {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.password_manager_leak_detection": False,
    },
)
opts.add_argument("--disable-features=PasswordLeakDetection")
```

For Firefox, geckodriver with no special options (Firefox doesn't have the modal problem).

If the probe is an **observation probe** running on Playwright, launch `chromium` headless with a fresh context — Playwright contexts are isolated and
profile-free, so the password-manager breach modal (a Selenium-Chrome-profile artefact) doesn't arise, and no prefs are needed.

### Step 4 — Build the scaffolding

Standard preamble for probes that need a login first:

```python
"""Probe: <one-sentence question>.

<2–4 sentence problem statement: what triggered this probe, what claim is
load-bearing, what evidence the probe is going to produce.>

Throwaway — delete once the finding lands in <test / comment / gap inventory / FRD>.
"""

from __future__ import annotations

import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

SITE = "<your-sut-url>"
LOGIN_URL = f"{SITE}/<login-path>"
# Import other URLs / selectors *exactly* as the production code uses them.
CHROMEDRIVER = sys.argv[1] if len(sys.argv) > 1 else "chromedriver"
ATTEMPTS = 4   # default; determinism check
```

If the probe needs to verify something with multiple attempts (deterministic? intermittent?), default to 4 attempts. Single-shot questions can run
once.

### Step 5 — Drive the exact target

The body. Open the screen the production code opens, in the state the production code reaches, wait the way the production code waits, do the action
the production code does. Then print state — `driver.current_url`, `driver.title`, `driver.page_source[:1000]`, `driver.get_cookies()`,
`driver.capabilities`, an element's `text` / `get_attribute("outerHTML")`, whatever the question asks for.

On an SPA, capture `page_source` or element text **only after the content has actually rendered** — wait on a real content marker, never read it off a
bare `get()` (see "SPA / reactive DOM — the traps").

No assertions in the test-framework sense. The probe **prints**; the human reads.

### Step 6 — Run it

```bash
.venv/bin/python <gitignored>/probe_<topic>.py <chromedriver-path>
```

If determinism matters, run with `ATTEMPTS = N` and read all N lines. If asymmetry between browsers matters, write **two** probes (one for each
driver) and run both. Don't fold them into one if it complicates the code path — readability of the probe is the readability of the finding.

### Step 7 — Read the output, write the finding

The output is the answer. Read it. Phrase the finding in one or two sentences with the empirical numbers:

- "Chrome stays on `/history` after `back()` post-logout (4/4 attempts), and a forced `refresh()` then redirects to `/` — confirms a BFcache hit on a
  `no-store` page."
- "The sidebar Logout link works 5/5 in clean Chrome with the password manager off. The 'jQuery dispatch race' comment is wrong; it was the breach
  modal misdiagnosed."
- "`/history` returns `Cache-Control: no-store, no-cache, must-revalidate` on a logged-out GET — the SUT does the right thing server-side; Chrome's
  BFcache restores anyway."

If the output is indeterminate, the probe is not done. Tighten the question, tighten the target, run again.

### Step 8 — Land the finding in a durable artifact

The probe is the _instrument_; the **finding** must live somewhere readers will see later:

| Where the finding goes                          | When                                                                                             |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| A scenario file's docstring / call-site comment | The finding shapes a test's assertion or POM behaviour. Cite path / function / observation.      |
| The gap inventory                               | The finding is a SUT defect, browser-behaviour finding, or test-env artifact.                    |
| The FRD's known-bugs section                    | The finding is user-facing.                                                                      |
| `CLAUDE.md` rule body                           | The finding generalises into a project-wide discipline (rare).                                   |
| A POM call-site comment                         | The finding is a localised "why this code does X" justification. Cite the probe's date + output. |

The finding must include a **source citation** — the source file/line, the rendered selector, the empirical count. Without it, the next reader can't
re-verify in seconds and the finding becomes a stale claim — exactly what `CLAUDE.md` → "Verify SUT behaviour" warns about.

### Step 9 — Delete the probe

Once the finding has landed:

```bash
/bin/rm <gitignored>/probe_<topic>.py
```

Leaving it around invites the next reader to revive the script rather than read the artifact that already answers the question. The probe has done its
job; the _answer_ is what matters.

## SPA / reactive DOM — the traps

On a server-rendered site (a PHP template) the DOM is complete the instant `driver.get()` returns — a bare print of `page_source` is the real page. On
a single-page app it is not, and three shortcuts silently break:

- **`page_source` straight after `get()` is the shell.** You print a loading skeleton or an empty `<div id="root">` and conclude "element absent".
  Wait for a real content marker first (the production wait condition, or Playwright's auto-wait). Never answer "does X render?" off an un-waited
  `get()`.
- **`page_source` is one snapshot.** A reactive DOM re-renders continuously; a single capture can catch a torn intermediate state no user ever saw.
  Wait for a stable condition, then capture — and for a transition, capture at named checkpoints, not once.
- **Raw HTTP never sees SPA-rendered content.** `httpx.get(url)` returns the shell; the content arrives afterwards over fetch. Raw HTTP answers
  headers / status / redirects — nothing about what the user actually sees.
- **Client-side routing is not an HTTP redirect.** An SPA route change is a history `pushState`: `current_url` changes with no server round-trip.
  Observing "the redirect chain" via `current_url` catches only _server_ redirects — for client-side navigation, watch the fetch traffic instead (CDP
  / Playwright network events).

The exact-target rule already shields **interaction** probes: mirror the production wait condition and you inherit whatever SPA-timing handling the
suite already has. These traps bite the **observation** probes — the ones reaching for `page_source` and raw HTTP as shortcuts.

## Templates (reach for them; don't write from scratch)

### Template A — single-shot browser probe

For quick browser-level questions — "where does this URL land?", "what's the page title?", "does this server redirect fire?". **Not** for response
headers (Selenium can't read them — Template E) and **not** for "does element X render?" on an SPA (a bare print catches the shell — Template C waits,
Template F auto-waits):

```python
"""Probe: <question>.

Throwaway — delete once the finding lands in <…>.
"""

from __future__ import annotations
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

opts = Options()
opts.add_argument("--headless=new")
# (clean chrome prefs as above if any post-login state is involved)
driver = webdriver.Chrome(service=Service(sys.argv[1]), options=opts)

try:
    driver.get("<sut-url>/<path>")
    print("url:", driver.current_url)
    print("title:", driver.title)
    # add the specific observation
finally:
    driver.quit()
```

### Template B — N-attempt determinism probe

For questions like "is this deterministic?", "is X a flake?":

```python
ATTEMPTS = 4
results = []
for i in range(ATTEMPTS):
    # do the thing
    observation = ...
    results.append(observation)
    print(f"attempt {i + 1}: {observation}")
print(f"\n{sum(1 for r in results if r)}/{ATTEMPTS} positive")
```

### Template C — login + post-login probe (use clean Chrome)

For questions about post-authenticated behaviour. Use the project's own demo credentials and selectors — the snippet below mirrors the shape used in
<https://github.com/mojo-molotov/ocarina-with-ai-example>:

```python
def _login(driver, w):
    driver.get(LOGIN_URL)
    w.until(ec.element_to_be_clickable((By.ID, "txt-username"))).send_keys(USERNAME)
    driver.find_element(By.ID, "txt-password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    w.until(ec.presence_of_element_located((By.XPATH, "//a[contains(text(),'History')]")))
```

### Template D — cross-browser probe

For questions like "does Chrome and Firefox differ on this?":

Two probes, one per browser, both run, results compared in prose afterwards. Don't fold them into one script — separate scripts keep the per-browser
path clean.

### Template E — server-response probe (raw HTTP)

For what the **server itself** sends — status, headers, `Set-Cookie`, the redirect chain. No JS, no browser. On an SPA this sees the **shell only** —
use it for headers / status / redirects, never for rendered content:

```python
"""Probe: <question about a server response>.

Throwaway — delete once the finding lands in <…>.
"""

from __future__ import annotations

import httpx

URL = "<sut-url>/<path>"

r = httpx.get(URL, follow_redirects=True)
print("final status:", r.status_code)
print("redirect chain:", [f"{h.status_code} {h.url}" for h in r.history])
print("cache-control:", r.headers.get("cache-control"))
print("set-cookie :", r.headers.get_list("set-cookie"))
```

### Template F — SPA content + network probe (Playwright)

For a reactive SPA where the rendered DOM is not in the initial HTML, or when the question is the fetch traffic behind a flow. Playwright auto-waits
for elements and exposes network and console events directly. Install once: `pip install playwright && playwright install chromium`.

```python
"""Probe: <question about SPA-rendered content or network behaviour>.

Throwaway — delete once the finding lands in <…>.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

URL = "<sut-url>/<path>"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    calls: list[str] = []
    page.on("response", lambda r: calls.append(f"{r.status} {r.request.method} {r.url}"))
    page.on("pageerror", lambda e: print("JS error:", e))

    page.goto(URL, wait_until="networkidle")  # settles after hydration + fetch
    # auto-waits for the real content marker — no explicit WebDriverWait needed:
    print("rendered:", page.locator("<exact production selector>").inner_text())
    print("network:")
    for c in calls:
        print(" ", c)

    browser.close()
```

> ⚠️ Playwright is the right **observation** tool, but it is **not** the production engine. A probe that reproduces a production _interaction path_
> (the synthetic-click question, the dispatcher question) must still use Selenium with the exact production target — see the rules. Reach for
> Playwright when the question is "what does the SUT render / fetch?", not "does our Selenium code's click land?".

## Rules — what a probe is, and isn't

- **A probe IS** — a one-off script, gitignored, no assertions, prints state, runs solo (not under `--workers`, not in CI), exercises the exact
  target, is deleted after the finding lands.
- **A probe IS NOT** — a test (no assertions, not in CI, not parallel-safe), a long-lived artifact (delete after), something to commit (gitignored), a
  vehicle for attack-shape inputs (per `CLAUDE.md` → "Security testing is functional and static — never active"), or a way to "see if a hack works"
  (the source-reading and exact-target rules apply).
- **Match the instrument to the question.** Selenium for production-interaction probes (exact target — mandatory). Raw HTTP for server responses only.
  Playwright or CDP for SPA-rendered content and network/timing observation. The wrong instrument yields a confident wrong answer — an un-waited
  `page_source` on an SPA "proves" an element missing when it simply hadn't rendered yet. See "Pick the tool for the question".

## Worked example

From a real session in <https://github.com/mojo-molotov/ocarina-with-ai-example>:

Question: "Was the historic `# jQuery dispatch race` comment on the sidebar's `logout()` correct, or was it the Chrome password-breach modal
misdiagnosed?"

Probe (`<gitignored>/probe_sidebar_logout.py`): builds clean Chrome (password manager off, mirroring `create_drivers_pool.py`) **and** plain Chrome
(default options) as a contrast, logs in with the demo creds, drives the **exact** locators the production code uses (`#menu-toggle` then
`#sidebar-wrapper a[href='authenticate.php?logout']`) with the **exact** wait condition (`element_to_be_clickable`), 5 attempts each.

Finding: clean Chrome 5/5 (works); plain Chrome breaks at varying post-credential points. Conclusion: the historic comment was wrong; the "race" was
the breach modal swallowing the click. Finding landed in the gap inventory (resolved-artifact section) and in `Sidebar.logout_via_sidebar`'s
docstring. Probe deleted.

## When to run this skill

- The user says: "probe X", "verify Y empirically", "let me run a quick experiment", "what does the page actually return?".
- Mid-investigation when you've stated `Fair point — I'm assuming. Let me verify empirically.` (per the `empiricism` skill).
- When a comment / docstring asserts a load-bearing SUT claim and `review-comment-drift` flagged it for re-verification.
- When `review-suite-stability` surfaces a surprise green or surprise red and the cause needs disambiguation.

## What this skill does NOT do

- It does not run the probe automatically on the user's machine — it produces the probe; the user (or downstream tool call) runs it.
- It does not add assertions to the probe. A probe prints; it doesn't pass/fail. If you want assertions, you want a test.
- It does not write the _finding_ into the durable artifact — the user (or a follow-up call) writes the comment / gap-inventory entry / spec-doc
  update. The probe gathers the evidence; the writing is a separate motion (see `empiricism`).
- It does not skip the deletion step. A probe that survives its finding is a probe that becomes stale and misleads.
