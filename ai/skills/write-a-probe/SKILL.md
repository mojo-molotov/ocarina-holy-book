---
name: write-a-probe
description: Author a one-off **probe** — a throwaway Python script that drives the browser (or raw HTTP) through a suspect flow and prints concrete runtime state (URL, page title, form HTML, hidden inputs, cookies, network observations) so you can see what the SUT actually does before encoding it as a test or accepting a claim about it. Probes bypass Ocarina entirely (no `create_selenium_test`, no suites, no assertions), live in a gitignored directory (`<gitignored>/`), are never committed, and are deleted once the finding lands in a durable artifact (a test, a source-cited comment, the gap inventory, the FRD). Use whenever the user asks to probe a flow, verify a behaviour empirically, capture rendered HTML, observe a redirect chain, measure inter-request timing, confirm a deployment-vs-source discrepancy, or settle a "does the SUT actually do X?" question. The hard rule: a probe must exercise the **exact** locator, screen, wait condition, and action the production code uses — never an "equivalent".
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

## Templates (reach for them; don't write from scratch)

### Template A — single-shot SUT-claim probe

For questions like "does this URL redirect?", "does this header come back?", "does this element render?":

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

## Rules — what a probe is, and isn't

- **A probe IS** — a one-off script, gitignored, no assertions, prints state, runs solo (not under `--workers`, not in CI), exercises the exact
  target, is deleted after the finding lands.
- **A probe IS NOT** — a test (no assertions, not in CI, not parallel-safe), a long-lived artifact (delete after), something to commit (gitignored), a
  vehicle for attack-shape inputs (per `CLAUDE.md` → "Security testing is functional and static — never active"), or a way to "see if a hack works"
  (the source-reading and exact-target rules apply).

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
