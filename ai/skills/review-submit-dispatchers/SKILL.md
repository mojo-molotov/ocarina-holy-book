---
name: review-submit-dispatchers
description:
  Audit POMs for **commit-style actions** (form submits, confirm buttons, anything a user "sends") that should be driven through a **random
  dispatcher** covering the legitimate browser interaction paths — click on the submit button, Enter on a focused text input (HTML implicit
  submission), Enter on the focused submit button — rather than hardcoded to one path. The random-dispatcher + `--workers N` cloning pattern is how
  this suite covers Enter-on-button regressions and Enter-on-input quirks without re-running every combination every test. Use whenever the user asks
  to review submit interactions, audit dispatcher coverage, check Enter-key coverage, review POM submit/confirm methods, or harden a form-handling
  POM. Surface gaps with the proposed dispatcher block; never auto-rewrite the POM.
---

# Review — submit/confirm dispatcher coverage

Audits POMs for **commit-style actions** that should run through a random dispatcher instead of hardcoding one interaction path. The point: a real
user can submit a form by clicking the button, pressing Enter in a text field, or pressing Enter on the focused submit button. A test that only ever
clicks misses Enter-on-button regressions; one that only ever presses Enter on a field misses click-handler regressions. Hardcoding one path silently
narrows what the suite probes.

The discipline (from `CLAUDE.md` → "Form submission paths"):

- `element.click()` on the submit `<button>` — always legitimate.
- `send_keys(Keys.ENTER)` on a focused text `<input>` — HTML implicit submission, legitimate **unless** a JS widget bound to that input intercepts
  Enter (CURA's Bootstrap datepicker on `txt_visit_date` is the example — Enter there toggles the calendar instead of submitting).
- `send_keys(Keys.ENTER)` on a focused `<button type="submit">` — a focused button activates on Enter; legitimate.

The audit surfaces gaps. **It never edits POMs.** A dispatcher is a deliberate API choice; the audit only makes the gap visible.

Default target: `src/pages/`. For a different target, ask the user.

## The pattern (worked examples in this repo)

`LoginPage._submit_dispatchers` — 4 paths:

```python
self._submit_dispatchers: dict[str, Effect] = {
    "click_login_button": lambda: (
        WebDriverWait(self._driver, timeout)
        .until(ec.element_to_be_clickable(self._btn_login))
        .click()
    ),
    "enter_on_username_field": lambda: (
        WebDriverWait(self._driver, timeout)
        .until(ec.element_to_be_clickable(self._txt_username))
        .send_keys(Keys.ENTER)
    ),
    "enter_on_password_field": lambda: (
        WebDriverWait(self._driver, timeout)
        .until(ec.element_to_be_clickable(self._txt_password))
        .send_keys(Keys.ENTER)
    ),
    "enter_on_focused_login_button": lambda: (
        WebDriverWait(self._driver, timeout)
        .until(ec.element_to_be_clickable(self._btn_login))
        .send_keys(Keys.ENTER)
    ),
}

def submit_login(self) -> LoginPage:
    self._submit_dispatchers[
        random.choice(list(self._submit_dispatchers.keys()))  # noqa: S311
    ]()
    return self
```

`AppointmentPage._submit_dispatchers` — 2 paths (no Enter-on-input because `txt_visit_date` has the Bootstrap datepicker intercept):

```python
"click_book_appointment_button": lambda: ...click(),
"enter_on_focused_book_appointment_button": lambda: ...send_keys(Keys.ENTER),
```

Each entry is a path; the public method (`submit_login`, `submit`) picks one with `random.choice` per call. Cycle repetition (`--workers N` cloning,
multiple cycles) covers the full path set across runs — no need to exercise every combination every time.

## What counts as a "commit-style action"

A POM method qualifies when **all** of these are true:

- It commits an intent (sends data, finalises an interaction, navigates _because_ of an explicit user click). Examples: a form submit, a "Confirm"
  button, "Send", "Save", "Place order", and — at the borderline — discrete commit-flavoured clicks like "Go to Homepage" on the empty-history page
  (REQ-HIST-4).
- It maps to a single underlying browser command (a click) but the same outcome is reachable via Enter on the focused button — and, for form submits
  with text inputs upstream, via Enter on those inputs.
- A miss on any one of those paths would be a real defect from a user's point of view.

It does **not** qualify when:

- The element isn't a button-like submit (a plain `<a href>` that navigates — Enter on the anchor is just the browser default, no value in a separate
  path).
- The action is a step _within_ a form (selecting a dropdown, ticking a checkbox, typing into a field). Those aren't commits.
- The "click" is sidebar navigation through a non-form path (`Sidebar` go-to-link methods — these are anchors with side-effects, and a dispatcher buys
  little). Surface only if the user explicitly asks.

## Method-name patterns to scan for

Search POMs for methods matching these patterns — first-pass candidates:

| Pattern                                                  | Examples in this repo                              |
| -------------------------------------------------------- | -------------------------------------------------- |
| `submit*`, `*_submit*`                                   | `LoginPage.submit_login`, `AppointmentPage.submit` |
| `confirm*`                                               | (none currently — would qualify if added)          |
| `book*`, `place*`, `send*`, `save*`                      | (none in this repo — generic patterns)             |
| `click_*` where the destination of the click is a commit | `HistoryPage.click_go_to_homepage` — borderline    |

The first two rows are **canonical commits**; flag if no dispatcher. The bottom rows are **borderline**; surface as judgment calls.

## Procedure

### 1. Locate POMs in the target

```bash
find <target> -name "*.py" -not -name "__init__.py"
```

### 2. Per POM, find commit-style methods

Read each method matching the patterns above. For each, classify how the method drives the action:

- **Hardcoded single path** — the method body is one `WebDriverWait(...).click()` or one `send_keys(Keys.ENTER)`, no dispatcher dict, no
  `random.choice`.
- **Random dispatcher** — the method body calls `random.choice` over a `dict[str, Effect]` (or equivalent) declared on the class.

### 3. Classify each method

| Tier      | When                                                                                                                                                                                                   |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **High**  | A canonical commit (`submit*`, `confirm*`) is hardcoded to one path. Must have a dispatcher.                                                                                                           |
| **Maybe** | A borderline commit (`click_go_to_homepage` and friends) is hardcoded to one path. Judgment call — flag with the trade-off.                                                                            |
| **Ok**    | Method uses a random dispatcher. Do not surface. Optionally note dispatcher composition if it looks thin (e.g. button-click only when the form has text inputs that should also be in the dispatcher). |

### 4. Diagnose each High / Maybe

For each, propose the dispatcher concretely:

- List the paths it should cover. Mirror existing naming (`click_<action>_button`, `enter_on_<field>_field`, `enter_on_focused_<action>_button`).
- **Skip Enter-on-input** if the field has a JS widget that intercepts Enter (Bootstrap datepicker, etc.). Note this explicitly when skipping.
- Write the dispatcher block as it would appear in the POM (matching the codebase's idiom: `dict[str, Effect]` keyed by path name; `random.choice`
  selection in the public method; `# noqa: S311` on the `random.choice` line).

### 5. Report

Use this exact template:

````markdown
# Submit-dispatcher audit — <target>

## High — canonical commit hardcoded to one path

- <pom>:<method>:<line> — currently drives only `<path>`. Misses: `<other paths>`.

  Current:

  ```python
  <method body>
  ```
````

Proposed dispatcher:

```python
<the dispatcher dict + public method>
```

Why it matters: <one or two sentences — what regression a missing path would hide>

## Maybe — borderline commit

- <same shape; explicitly note the trade-off>

## Summary

- High: N | Maybe: N
- Verdict: <add dispatchers to N methods | nothing to change | …>

````

Print the report; do not write it to a file unless the user asks. Also update `CURA_TEST_STRATEGY.md` §4's dispatcher table when the user accepts a change — but never as part of the audit; that's the follow-up edit.

### 6. Stop. The user decides.

Do not edit POMs. Do not propose a sweeping fix commit. The dispatcher composition is a per-form judgement (the Enter-on-input caveat for datepicker
inputs is the canonical case). Surface the proposal; the user picks the paths.

## Examples

### Good — canonical commit with a dispatcher (do **not** surface)

`LoginPage.submit_login` and `AppointmentPage.submit` (see the worked examples at the top of this file). Each declares `_submit_dispatchers` and
selects via `random.choice`. Multiple paths covered; missing paths are documented (Enter-on-`txt_visit_date` is intentionally absent because of the
datepicker intercept).

### Violation — would surface as **High**

```python
# hypothetical SearchPage
class SearchPage(...):
    _btn_search = (By.ID, "btn-search")

    def submit_search(self) -> SearchPage:
        WebDriverWait(self._driver, get_timeout()).until(
            ec.element_to_be_clickable(self._btn_search)
        ).click()
        return self
````

`submit_search` is hardcoded to a click. An Enter-on-focused-button regression in the search form would silently slip past this. Report would propose:

```python
self._submit_dispatchers: dict[str, Effect] = {
    "click_search_button": lambda: (
        WebDriverWait(self._driver, timeout)
        .until(ec.element_to_be_clickable(self._btn_search))
        .click()
    ),
    "enter_on_focused_search_button": lambda: (
        WebDriverWait(self._driver, timeout)
        .until(ec.element_to_be_clickable(self._btn_search))
        .send_keys(Keys.ENTER)
    ),
    # If SearchPage has a `_txt_query` text input that doesn't have a widget
    # intercepting Enter, also add:
    "enter_on_query_field": lambda: (
        WebDriverWait(self._driver, timeout)
        .until(ec.element_to_be_clickable(self._txt_query))
        .send_keys(Keys.ENTER)
    ),
}

def submit_search(self) -> SearchPage:
    self._submit_dispatchers[
        random.choice(list(self._submit_dispatchers.keys()))  # noqa: S311
    ]()
    return self
```

### Borderline — would surface as **Maybe**

`HistoryPage.click_go_to_homepage`: an `<a>`-tag click on the empty-history "Go to Homepage" button (REQ-HIST-4). A click is the user-canonical path;
Enter on the focused anchor is also a valid user action. Report would note the path is single-click, flag it as Maybe, and let the user decide whether
the symmetry warrants a 2-path dispatcher here.

## When to run this skill

- The user asks: "are the submit paths covered?", "review dispatchers", "is there Enter-key coverage on this form?", "audit POM submits".
- A PR adds or modifies a POM method that commits (submits, confirms, sends).
- A new POM with a form is introduced.
- A release-hardening pass.

You may run it without prompting if a diff you're already reviewing adds a `submit*` / `confirm*` method without a dispatcher.

## What this skill does NOT do

- It does not edit POMs.
- It does not exhaustively enumerate every interaction path on every action — the point is **commit-style** actions specifically, where multiple paths
  are realistic and a miss is a real defect.
- It does not enforce running every combination per test — `random.choice` + `--workers N` cloning + cycle repetition is by design how coverage adds
  up across runs. The audit only checks that the dispatcher exists; running it is the framework's job.
- It does not maintain `CURA_TEST_STRATEGY.md` §4's dispatcher table. When a dispatcher is added or removed, that table updates in the same PR as the
  POM change — but that's authoring, not auditing.
