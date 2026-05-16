---
name: review-comment-drift
description:
  Audit Python comments and docstrings for **drift** — claims that no longer match the code or the SUT. Walk POMs first (call-site comments asserting
  SUT behaviour are the highest-rot risk — they outlive the deployment that motivated them), then scenario inline comments and dataset annotations,
  then the scenario top docstring (the `Flow:` arrow chain and the `Pre-fragments:` list — these are also mechanically checkable against the actual
  `drive_page` sequence and the `pre_test_scenarios_fragments` kwarg). Surface drifted comments with the empirical contradiction; never silently
  rewrite a comment — a stale comment may signal a stale *test*, and "fixing" the comment to match the code can paper over the real defect. Use
  whenever the user asks to audit comments, review documentation drift, vet comment freshness, or harden after a refactor / deployment change.
---

# Review — comment drift

Audits a Python source tree for **comments and docstrings that have drifted from the code or the SUT they describe**. The order is deliberate,
weakest-link first:

1. **POMs** — call-site and selector comments asserting things like _"the SUT does X"_, _"the deployed form has no CSRF"_, _"this Bootstrap 3 hook
   intercepts Enter"_. These rot the moment the SUT or the deployment changes. They're often _the only_ place that "why" is recorded; when wrong, they
   actively mislead.
2. **Scenario inline comments + dataset annotations** — call-site comments inside scenario files, and comments around dataset constants (`_FACILITY`,
   `_VISIT_DATES`, `booking_cases`). These rot when the dataset changes or when a connector signature evolves.
3. **Scenario top docstring** — the `Flow:` arrow chain, the `Pre-fragments:` / `Post-fragments:` lists, the one-paragraph summary. These are also
   **mechanically checkable** against the actual `drive_page` sequence and the `create_selenium_test` kwargs, so the audit can do them cheaply.

This skill surfaces findings. **It never silently rewrites a comment.** A stale comment is sometimes a signal that the _test or the POM_ is stale —
"fixing" the comment to match the code can paper over a real defect. The user decides per finding whether to update the comment, update the code, or
update both.

Default target: `src/`. For a different target, ask the user.

## What "drift" looks like

Concrete patterns the audit goes looking for:

| Drift class                                                               | Where                                                                                                                                                                         | How to detect                                                                                                                           |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **SUT claim no longer matches the deployment**                            | POMs (call-site comments around `driver.execute_script`, `send_keys`, `click()`); the gap inventory entries already covered by tests                                          | Re-verify the claim against current PHP / live HTML / a probe. The CLAUDE.md "Verify SUT behaviour — don't theorise" rule applies.      |
| **Scenario `Flow:` chain doesn't match the actual `drive_page` sequence** | Scenario top docstring                                                                                                                                                        | Count `drive_page(...)` blocks; for each, list the connectors used in the chain order; compare against the arrows in the docstring.     |
| **`Pre-fragments:` / `Post-fragments:` list doesn't match the kwarg**     | Scenario top docstring                                                                                                                                                        | Parse `create_selenium_test(... pre_test_scenarios_fragments=[...], post_test_scenarios_fragments=[...])` and compare to the docstring. |
| **File / class / method reference no longer exists**                      | Any comment naming a path or symbol (e.g. `# see logout.py`, `# delegates to AppointmentPage.logout()`)                                                                       | grep the named path / symbol. Missing → drift.                                                                                          |
| **Line-number reference is stale**                                        | Comments like `# see line 42 of foo.py`                                                                                                                                       | Resolve the cited line — does it still match the described content?                                                                     |
| **Selector comment doesn't match the locator / DOM**                      | POM selector blocks (`_btn_login = (..., "button[type='submit']")  # matches the login submit`)                                                                               | Verify against rendered HTML (probe) when the description is specific.                                                                  |
| **Dataset comment doesn't match the dataset**                             | Dataset modules and inline `_FACILITY = "..."`-style constants with a justifying comment                                                                                      | Match the comment against the literal value(s).                                                                                         |
| **"Why" comment cites an incident that's resolved**                       | Anywhere — `# because Chrome's password modal swallows input` is fine _after_ the driver adapter fix; `# because Chrome's password modal still swallows input` would be wrong | Read the comment; trace the cited issue to the gap inventory (is it marked resolved? what's its current status?).                       |

## Procedure

Walk the three layers in order. Stop at each level long enough to surface findings; don't barrel through to the next level if the first is full of
drift.

### Layer 1 — POMs

```bash
find <target>/pages -name "*.py" -not -name "__init__.py"
```

For each POM file:

1. Read every `#` comment and method docstring.
2. Classify each:
   - **SUT claim** (asserts something about the SUT's runtime behaviour) — flag for empirical re-verification per the `empiricism` skill / CLAUDE.md
     "Verify SUT behaviour".
   - **Code-shape claim** (asserts something about _the codebase_'s shape — naming a file/method/selector, citing a line) — flag for mechanical
     re-verification (grep / line resolution).
   - **Rationale / why** — flag for re-verification against the gap inventory and recent PRs.

For SUT claims, pick the cheapest verification (PHP read → live HTML → probe). If the audit context is read-only, mark the finding _"not verified —
read-only audit; cite path-to-verification in report."_

### Layer 2 — scenario inline comments + datasets

```bash
find <target>/tests/scenarios -name "*.py" -not -name "__init__.py"
```

Per scenario file:

1. Walk inline `#` comments inside `_scenario_*` bodies and `drive_page(...)` blocks. Same classification as Layer 1.
2. Walk dataset annotations: the comments around `_FACILITY`, `_VISIT_DATES`, `booking_cases`, `logout_cases`, inline `LoginCase(...)` constructions
   in `failed_logins.py`. Cross-check the comment text against the actual values.
3. For data-driven datasets stored under `tests/scenarios/<feature>/datasets/`, walk those files specifically — they're often where stale "covers the
   X / Y / Z cases" comments live.

### Layer 3 — scenario top docstring (mechanically checkable)

Two checks, both mechanical, both cheap:

**3a. `Flow:` chain vs actual `drive_page` sequence.**

Parse the file with `ast.parse`. Walk the `_scenario_*` function body. For each `drive_page(...)` call (the args list, in order), record the
connectors of every `act(...)` chain inside. The result is the actual flow as a list of (pom, connector) pairs in execution order.

Compare against the docstring's `Flow:` arrow chain. If the docstring says `open page → fill form → submit → verify confirmation`, but the actual flow
is `open page → fill form → submit → open history → verify history`, that's drift.

A tolerant comparison is fine — the docstring uses prose ("submit"), the code calls `submit_appointment`; loose match on the verb is OK. The flag
fires when the _shape_ changes: an act added or removed, the order swapped, a verify renamed to something semantically different.

**3b. `Pre-fragments:` / `Post-fragments:` lists vs kwargs.**

Parse `create_selenium_test(...)` calls (one or more in a single file for data-driven). For each, extract `pre_test_scenarios_fragments=[…]` and
`post_test_scenarios_fragments=[…]`. Cross-check against the docstring's `Pre-fragments:` / `Post-fragments:` lines.

Note: the docstring should say `(none)` rather than omit a section — _that_ convention is documented in CLAUDE.md's "Scenario file structure" rule. If
the docstring omits a section, flag it too.

### Layer 4 (optional) — the gap inventory and the FRD

If the user wants to extend the audit:

- Each the gap inventory entry citing a file / line / function — verify the reference still resolves (the renamed-file trap).
- Each the gap inventory entry whose "resolution" cites a code change — verify the cited code is still present (e.g. §A-ENV-2 cites
  `create_drivers_pool.py` disabling the password manager; verify those options are still set).

## Classify each finding

| Tier      | When                                                                                                                                                      |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **High**  | SUT claim contradicted by the current PHP / live HTML / probe. The comment actively misleads — would seed a workaround if a future contributor trusts it. |
| **High**  | Mechanical drift the audit can prove: `Flow:` chain mismatched, `Pre-fragments` mismatched, named-symbol no longer exists.                                |
| **Maybe** | "Why" rationale cites an incident; need user judgment on whether it still applies.                                                                        |
| **Maybe** | Selector comment claims something about the DOM that needs a live check (probe required).                                                                 |
| **Low**   | Stylistic / cosmetic drift — typo, outdated phrasing, slightly stale wording where the claim is still substantially right.                                |

## Report

Use this exact template:

```markdown
# Comment-drift audit — <target>

## Layer 1 — POMs

### High

- <path>:<line> — `<comment text>` — contradicted by <evidence>.
  - Likely cause: <one-line>
  - Recommendation: <update the comment / update the code / re-verify with a probe>

### Maybe

- <path>:<line> — <same shape>

## Layer 2 — scenarios (inline + datasets)

### High / Maybe

- <same shape>

## Layer 3 — scenario top docstrings

### High — mechanical mismatch

- <path>:1 — `Flow:` chain has <N> arrows; the actual `drive_page` sequence has <M>. Drift:
```

docstring: open appointment form → fill → submit → verify confirmation actual: open appointment form → fill → submit → verify confirmation → open
history → verify history card

```

- <path>:1 — `Pre-fragments: (none)` in docstring; `pre_test_scenarios_fragments=[login_as_demo_user]` in code.

### Maybe — wording drift

- <path>:1 — <…>

## Summary

- High: N | Maybe: N | Low: N
- Verdict: <…>
```

Print the report; do not write it to a file unless the user asks. **Do not silently rewrite any comment.** A stale comment can signal a stale test;
let the user decide which side to fix.

## Stop. The user decides.

Each finding has at least two possible fixes:

- Update the comment to match current reality.
- Update the code (or the test) because the comment was _correct_ and the code drifted.

Either is sometimes right. The audit's job is to surface the contradiction, not to choose.

## Examples

### High — POM SUT claim drift

```python
# AppointmentPage.logout (historical)
def logout(self) -> AppointmentPage:
    """Log out by navigating directly to the logout URL.

    Same observable behaviour as clicking the sidebar logout link, without
    the jQuery dispatch race that proved unreliable in headless Chrome.
    """
    self._driver.get(LOGOUT_URL)
```

The comment claims a _jQuery dispatch race_ makes the sidebar path unreliable in headless Chrome. A probe (`gh api` on the rendered HTML + a
clean-Chrome session) shows the Logout link is a plain `<a href>` — no jQuery dispatches the navigation. The comment is wrong; the "race" was the
Chrome password-breach modal misdiagnosed. The audit's report cites the probe evidence; the user decides whether to rewrite the comment or restore the
missing context elsewhere (in the codebase, the comment was already corrected when `Sidebar.logout()` moved off `AppointmentPage`).

### High — `Flow:` mismatch

```python
"""Book an appointment.

Flow:
  open appointment form → fill → submit → verify confirmation

Pre-fragments: login_as_demo_user
Post-fragments: (none)
"""

def _scenario(driver, logger):
    return [
        drive_page(
            act(on_appointment, open_appointment_page)...,
            act(on_appointment, fill_appointment(...))...,
            act(on_appointment, submit_appointment)...,
        ),
        drive_page(act(on_confirmation, verify_booking_confirmed)...),
        drive_page(  # ← this drive_page is not in the docstring's Flow:
            act(on_history, open_history_page)...,
            act(on_history, verify_booking_in_history(...))...,
        ),
    ]
```

The docstring stops at `verify confirmation`; the actual flow continues to history. Drift. Recommendation: extend the docstring's `Flow:` arrows to
match.

### Maybe — rationale drift

```python
# create_drivers_pool.py
# Disable the consumer password manager so Chrome's breach modal doesn't swallow
# clicks after the demo password is entered.
```

The rationale is correct (per §A-ENV-2). The audit would surface this as **Low / Ok** — verifies against the GAPS file; no drift. But if the gap
inventory later marks §A-ENV-2 as obsolete (Google removed leak detection, say), this comment would become **Maybe** and need a fresh evaluation.

## Hard filters — what this skill does NOT surface

- **Comments inside `__pycache__/` or generated files** — not maintained by hand.
- **`# noqa: <rule>` suppressions** — those are lint comments, not documentation; the `review-type-ignore` skill (and analogous future audits for ruff
  suppressions) handles them.
- **`TODO` / `FIXME` / `XXX` / `HACK` markers** — those are explicit tracking comments, handled by the `manage-backlog` skill's TODO scan.
- **Comments inside throwaway probes** in `<gitignored>/` — by definition not maintained.

## When to run this skill

- The user asks: "audit comments", "are comments still accurate", "vet doc-drift", "review docstrings", "is this docstring still right?"
- After a refactor that touched POMs or scenario shapes (the most fertile soil for `Flow:` and `Pre-fragments:` drift).
- After the SUT's deployment changes or after a gap-inventory entry is added / resolved.
- Before a release-hardening pass.

## What this skill does NOT do

- It does not rewrite any comment or docstring.
- It does not run a full SUT verification — it surfaces _candidates_ for verification and points at the cheapest tool (per the `empiricism` skill).
- It does not chase typos in code (variable names, identifier casing) — only the documentation/comment layer.
- It does not flag missing comments. The discipline of "when to write a comment" is in `CLAUDE.md`; missing comments are a separate concern, not
  drift.
