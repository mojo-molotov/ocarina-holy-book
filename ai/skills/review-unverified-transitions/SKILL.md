---
name: review-unverified-transitions
description:
  Audit Ocarina scenario files for `drive_page` blocks that transition to (or to-and-from) a page without verifying the resulting page. The rule is
  absolute — **every transitioning `drive_page` must be followed by a verify of where it landed**, either as a verify act in the same `drive_page` or
  as the first act of the next `drive_page` (or, equivalently, chained inside the connector). A transition without a verify proceeds blind; the next
  act runs in an unconfirmed state, and a regression there manifests as a confusing downstream timeout rather than a clear "we never reached the
  page". Use whenever the user asks to review scenarios, audit `drive_page` discipline, find unverified transitions, or harden a scenario file. Run
  defensively after writing or modifying any scenario — that's when these slip in.
---

# Review — transitions without verify

Audits Ocarina scenario files (`src/tests/scenarios/**/*.py`) for `drive_page` blocks that move to a different page — by opening it, by submitting a
form, by clicking a sidebar link, by logging out, by navigating back/forward — without then verifying the resulting page.

The rule: **open + verify, always.** Either two acts in the same `drive_page`:

```python
drive_page(
    act(on_history, open_history_page).failure(...).success(...),
    act(on_history, verify_history_page).failure(...).success(...),
),
```

or split across two `drive_page`s when the verification target is a different POM:

```python
drive_page(
    act(on_sidebar, logout_session).failure(...).success(...),
),
drive_page(
    act(on_home, verify_homepage).failure(...).success(...),
    ...
),
```

or — equivalently — both folded into the connector itself (none of the current connectors do this; if one does, treat it as covered).

A transition without a verify is **blind**: the next step runs in an unconfirmed state, and a regression upstream surfaces as a confusing downstream
timeout instead of a clear "we never reached the page".

Default target: `src/tests/scenarios/`. For a different target, ask the user.

The audit surfaces violations only. **It never edits scenario files.** Hand the report over and let the user decide whether to fix in this PR or
follow up.

## Transition vocabulary (the load-bearing dataset)

A `drive_page` is **transitioning** if its terminal act calls one of these connectors. Each pairs with the verify(es) that must follow:

| Transitioning action                                                  | Lands on                                    | Required verify(es)                                                                                                         |
| --------------------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `open_home_page`, `navigate_home_via_sidebar`, `click_go_to_homepage` | homepage                                    | `verify_homepage`                                                                                                           |
| `logout_session`, `logout_via_sidebar`                                | homepage                                    | `verify_homepage`                                                                                                           |
| `open_login_page`, `navigate_to_login_via_sidebar`                    | login page                                  | `verify_login_page` / `verify_login_success` / `verify_login_failed`                                                        |
| `login_with_credentials`                                              | authenticated context (login-page-side)     | `verify_login_success` or `verify_login_failed`                                                                             |
| `open_history_page`, `navigate_to_history_via_sidebar`                | history page (or redirect if logged out)    | `verify_history_page` or `verify_history_inaccessible`                                                                      |
| `open_appointment_page`                                               | appointment form (or redirect)              | `verify_appointment_page` or `verify_appointment_inaccessible`                                                              |
| `open_profile_page`, `navigate_to_profile_via_sidebar`                | profile (or redirect)                       | `verify_profile_page` or `verify_profile_inaccessible`                                                                      |
| `submit_appointment`                                                  | confirmation (or stays on form if rejected) | `verify_booking_confirmed` or `verify_booking_not_confirmed`                                                                |
| `navigate_back_to_history`, `navigate_forward_from_history`           | wherever the back-forward stack lands       | one of `verify_back_button_did_not_restore_history`, `verify_history_inaccessible`, `verify_history_inaccessible_on_reload` |

The accepted **verify vocabulary** (must start with `verify_`): `verify_homepage`, `verify_login_page`, `verify_login_success`, `verify_login_failed`,
`verify_history_page`, `verify_history_inaccessible`, `verify_history_inaccessible_on_reload`, `verify_appointment_page`,
`verify_appointment_inaccessible`, `verify_profile_page`, `verify_profile_inaccessible`, `verify_profile_has_no_form_fields`,
`verify_booking_confirmed`, `verify_booking_not_confirmed`, `verify_back_button_did_not_restore_history`, `verify_facility_in_history`,
`verify_visit_dates_in_history`, `verify_history_date_order`, `verify_history_is_empty`, `verify_has_appointments`, `verify_booking_in_history`,
`verify_*_on_confirmation`.

If the project adopts a new action or verify, add it here. Treat additions to either column as a dataset change — surface the proposed addition before
editing this list (see `CLAUDE.md` → "Datasets are authoring decisions").

## Component-`drive_page` transitions — same rule, named explicitly

A `drive_page` may wrap a _component_ interaction rather than a page interaction (driving the `Sidebar`, toggling a widget). The screenshot rule in
`CLAUDE.md` has a dedicated exception for the component case; **the unverified-transition rule has no such exception**. If the component interaction
causes the browser to change page — logout, sidebar nav, any future widget that triggers a navigation — the destination must still be verified.

Two practical points:

- **The verify is on the destination POM, not on the component.** A `drive_page(act(on_sidebar, logout_session))` is followed by an
  `act(on_home, verify_homepage)` — either as a second act inside the same `drive_page` (when the destination POM is already in scope of that
  `drive_page`'s acts) or as the first act of the next `drive_page`.
- **A component `drive_page` that does NOT transition is out of scope.** A hypothetical `drive_page(act(on_sidebar, open_sidebar))` that only slides
  the menu in — no navigation — has nothing for this skill to flag. The screenshot rule's exception may still apply to it (was the slide-in visible to
  the user?), but that is a different audit.

In the worked example (<https://github.com/mojo-molotov/ocarina-with-ai-example>), the post-logout test family (`post_logout_bfcache_exposure`,
`post_logout_server_invalidation`, `post_logout_access`, `post_logout_frenetic_navigation`, `rapid_logout_relogin`'s cycle logouts, and `logout.py`'s
two data-driven cases) all have a `drive_page` whose terminal act is `logout_session` / `logout_via_sidebar`. Each one is exactly the case this rule
targets. Expect them to surface as **Violations** on a first run — and check the proposed fix per file: in most of them the homepage isn't the focus,
so the cheapest fix is a small intermediate `drive_page` with `act(on_home, verify_homepage)`; in `logout.py` the verify is _already_ present (it owns
the homepage frame), so it's the correct shape, not a violation.

## What is NOT a transitioning action (do not flag)

These stay on the same page and don't need a downstream verify just for transition's sake:

- `fill_appointment`, `fill_appointment_without_date`, `enter_username`, `enter_password`, `enter_comment`, `enter_visit_date`
- `press_enter_on_visit_date` (purpose is to NOT transition — verified by the next drive_page's `verify_booking_not_confirmed`)
- `bypass_visit_date_validation` (DOM manipulation, no navigation)
- `check_readmission`, `select_facility`, `select_program` (form fill)

A `drive_page` whose terminal act is one of these is not in scope.

## Procedure

### 1. Locate scenarios in the target

```bash
find <target> -name "*.py" -not -name "__init__.py"
```

For a diff/branch audit, restrict:

```bash
git diff --name-only main..HEAD -- 'src/tests/scenarios/**.py'
```

### 2. Per scenario file, find every `drive_page(...)` block

A `drive_page` is a multi-line call. The terminal act of the block is the **last** `act(...)` chain before the closing `)`. Read the block; identify
the last `act(<pom>, <connector>)`.

For precision over many files, walk the AST (`ast.parse` → find `ast.Call` nodes whose `func.id == "drive_page"`, then iterate the `args` to get the
chained `act(...)` calls; the last one's second argument is the terminal connector).

### 3. Classify each `drive_page`

| Tier          | When                                                                                                                                                                                                                                                       |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Violation** | Terminal act is a **transitioning action** (from the table above) AND neither (a) the same `drive_page` includes a `verify_*` act on the destination POM, nor (b) the immediately next `drive_page` _starts_ with a `verify_*` act on the destination POM. |
| **Maybe**     | Terminal act is transitioning, _some_ verify follows in the next `drive_page` but on a different POM than the destination (e.g. logout lands on home but the next dp starts on history). Surface as a judgment call.                                       |
| **Ok**        | Either non-transitioning terminal act, or a `verify_*` of the right POM follows as required. Do not surface.                                                                                                                                               |

### 4. Diagnose each Violation / Maybe

For each, name:

- The transitioning action.
- Where it lands (per the dataset table).
- What verify is missing (or is mismatched in the Maybe case).
- The proposed fix — concrete, not hand-wavy. Either add an `act(<destination_pom>, verify_<destination>)` to the same `drive_page` (when destination
  POM is in scope) or insert a `drive_page` with the verify before the next step.

### 5. Report

Use this exact template:

````markdown
# Unverified-transition audit — <target>

## Violation — transitioning `drive_page` with no verify

- <path>:<line> — `<terminal connector>` transitions to <destination>; no `verify_<destination>` follows.

  Current:

  ```python
  <the offending drive_page block, plus the following one if relevant>
  ```
````

Proposed fix:

```python
<the drive_page with the verify added — or a new drive_page inserted>
```

Why it matters: <one-line — what regression would manifest blindly>

## Maybe — verify follows but on a different POM

- <same shape; explicitly note the mismatch>

## Summary

- Violations: N | Maybes: N
- Verdict: <ship after fixing the N violations | nothing to change | …>

````

Print the report; do not write it to a file unless the user asks.

### 6. Stop. The user decides.

Do not edit. Do not propose a sweeping fix commit. A Maybe might be deliberate (a scenario probing exactly that no verify is needed because the next step's verification is sufficient). The audit's job is visibility.

## Examples

### Violation (would surface as **Violation**)

```python
# scenario excerpt — logout drive_page has no verify, next dp moves on
drive_page(
    act(on_sidebar, logout_session)
    .failure(log_error("Failed to logout"))
    .success(log_and_screenshot("Logged out")),
),
drive_page(
    act(on_history, open_history_page)
    ...
)
````

`logout_session` lands on the homepage. The next `drive_page` doesn't `verify_homepage` — it jumps straight to opening history. If logout silently
failed (or landed somewhere unexpected), the open-history step would either succeed (because we're still logged in!) or fail with a confusing timeout.
The report would propose either:

```python
drive_page(
    act(on_sidebar, logout_session).failure(...).success(...),
    act(on_home, verify_homepage).failure(...).success(...),  # added
),
```

or a dedicated `drive_page(act(on_home, verify_homepage))` between the two.

### Ok (do **not** surface)

```python
drive_page(
    act(on_history, open_history_page).failure(...).success(...),
    act(on_history, verify_history_page).failure(...).success(...),  # ← verify in same dp
),
```

Same `drive_page` opens and verifies. Correct shape.

### Ok across two drive_pages (do **not** surface)

```python
drive_page(
    act(on_sidebar, navigate_to_login_via_sidebar).failure(...).success(...),
    act(on_login, verify_login_page).failure(...).success(...),  # ← verify in same dp
),
```

The sidebar-component drive_page chains the verify in the same block — covered.

### Maybe (would surface as **Maybe**)

```python
drive_page(
    act(on_appointment, submit_appointment).failure(...).success(...),
),
drive_page(
    # Skips verifying confirmation directly; opens history and verifies the
    # booking landed there. The booking-confirmed page was never asserted.
    act(on_history, open_history_page).failure(...).success(...),
    act(on_history, verify_booking_in_history(...))
    ...
)
```

`submit_appointment` lands on confirmation; the next dp verifies the _downstream effect_ in history rather than the immediate destination. The proof
is arguably stronger (the booking really persisted) but the immediate transition isn't asserted, so a regression where the form silently no-ops would
still surface — just one step later. Report it as a judgment call.

## When to run this skill

- The user asks: "review the scenarios", "audit `drive_page` discipline", "find unverified transitions", "is this scenario well-formed?"
- A PR adds or modifies a scenario file.
- A refactor touches a connector that transitions (`logout`, `submit_appointment`, anything on `Sidebar`).
- A release-hardening pass.

You may run it without prompting if a diff you're already reviewing modifies scenarios.

## What this skill does NOT do

- It does not edit scenario files.
- It does not flag drive_pages whose terminal act is non-transitioning (form-fill, DOM manipulation, key-press).
- It does not enforce screenshot rules, log-message rules, or other scenario conventions — those belong to other audits and to the conventions in
  `CLAUDE.md`.
