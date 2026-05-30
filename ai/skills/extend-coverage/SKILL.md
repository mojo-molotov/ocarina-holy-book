---
name: extend-coverage
description:
  Compare the declared test strategy (the test-strategy doc) and the actual test inventory against the codebase to surface **adjacent test cases that
  aren't covered yet** — variants one input/parameter away from an existing test, sibling pages where the same operation is also possible, dispatcher
  paths not exercised, documented gaps without an intentional-fail test, edge values at the boundaries of inputs. The output is a structured list of
  *candidate* tests with rationale and priority — never a written scenario. The user decides what's worth adding. Use whenever the user asks to find
  coverage gaps, extend the suite, look for missing test cases, hunt for adjacent scenarios, harden before release, or do a coverage pass.
---

# Extend coverage — find unexercised adjacent cases

Walks the strategy doc + the actual test inventory + the codebase to surface **adjacent** test cases that aren't covered. "Adjacent" means one of:

- **Same flow, different parameter** — an existing test uses input value X; siblings of X are unexercised.
- **Same operation, different page** — an existing test does operation Y on page A; page B (where Y is also possible) isn't tested.
- **Same page, different operation** — page A has tested operations Op1, Op2; Op3 (in scope per the strategy) is missing.
- **Dispatcher path uncovered by any test** — a random-dispatcher path exists in a POM but no test deterministically exercises it.
- **Documented gap with no intentional-fail test** — a known SUT defect in the gap inventory or FRD without an assertive test pinning it.
- **Edge value at an input boundary** — empty, very long, leading/trailing whitespace, mixed case, special characters; only where a real user could
  plausibly produce that value.

The output is a **candidate list**, never a written test. The user decides what to add and what to drop. The skill's job is visibility.

Default target: the project (the test-strategy doc + `src/`). For a different repo, ask the user.

## Adjacency dimensions (the load-bearing dataset)

Walk these in order; surface candidates per dimension.

### 1. Same flow, different parameter

For each existing test that varies an input parameter (e.g. in <https://github.com/mojo-molotov/ocarina-with-ai-example>: `failed_logins` cases,
`booking_cases`, `logout_cases`, the visit-date offset, the comment string), list the _sibling values_ in the same dimension that no test covers.
Filter by "would a real user plausibly produce this value?" — per `CLAUDE.md` → "Functional testing simulates a real human". Drop exotic/synthetic
values.

Examples of dimensions worth walking (illustrated from <https://github.com/mojo-molotov/ocarina-with-ai-example>):

- **Username casing / whitespace** — covered: invalid, empty, lowercase, uppercase. Uncovered (and a real user could plausibly do these):
  leading/trailing whitespace, mixed case like `John doe`, doubled space inside (`"John  Doe"`).
- **Submit payload variations** — covered: 3 facility×program triples. Uncovered: empty `comment`, very long `comment` (paste from clipboard),
  facility/program pair never combined in the dataset.
- **Date boundaries** — covered: in_days(7), in_days(14), in_days(21), in_days(45), in_days(60), in_days(90+n), in_days(-1). Uncovered boundaries that
  a real user could pick: today (in_days(0)), one year out (in_days(365)), February 29 in a leap year, etc.

### 2. Same operation, different page

For each test exercising a _page-class_ operation (back-button, sidebar nav, logout, unauthenticated access, etc.), list the sibling pages where the
same operation is possible but no test runs it.

- **Back-button BFcache** — covered: history. Uncovered: appointment (after a successful booking → logout → back), profile.
- **Unauthenticated access** — covered: history, appointment, profile. Uncovered: any other auth-gated URL (the direct path vs a fragment form;
  variants without a hash router).
- **Sidebar nav (authenticated)** — covered: Home, History, Profile, Logout. The Login link is logged-out only and covered separately. **Done — flag
  none.**
- **Logout mid-flow** — covered: logout from a clean authenticated state. Uncovered: logout while a form is partially filled (appointment form
  mid-fill). Realistic? — borderline; surface as low priority.

### 3. Same page, different operation

For each page POM, list every public method (the page's exposed operations) and check whether a test exercises each one. Methods declared and never
called from a scenario are dead surface (already caught by the "no dead connectors" rule — `review-dead-code` audits this end-to-end); methods called
only as setup, never as the subject of a test, are coverage gaps.

Concrete examples from <https://github.com/mojo-molotov/ocarina-with-ai-example>:

- For `HistoryPage`: `verify_has_appointments` exists. Covered by `view_history`? `verify_history_date_order` exists. Covered by `history_ordering`.
  `verify_is_empty` covered by `empty_history`. Etc.
- For `AppointmentPage`: `remove_visit_date_required` covered by `server_side_date_bypass`. `press_enter_on_visit_date` covered by
  `enter_on_visit_date_no_submit`. Etc.

### 4. Dispatcher path uncovered by any test

In the worked example (<https://github.com/mojo-molotov/ocarina-with-ai-example>): `LoginPage._submit_dispatchers` has four paths
(`click_login_button`, `enter_on_username_field`, `enter_on_password_field`, `enter_on_focused_login_button`); `AppointmentPage._submit_dispatchers`
has two. Across `--workers N` cloning and cycle repetition, the random choice covers them probabilistically, not deterministically. Surface dispatcher
paths that haven't been deterministically pinned by at least one test in CI history (or by a deterministic-path opt-in if the user wants such a
thing).

Caveat: this dimension is intentionally probabilistic — the project's design says exhaustive coverage isn't worth it. Flag as `priority: P3`
informational unless a specific path has reason to be deterministically exercised (e.g. a known regression on that path).

### 5. Documented gap with no intentional-fail test

The FRD's known-bugs section (and the gap inventory) enumerate known SUT defects. Each one _should_ have an intentional-fail test pinning it.
Cross-check entry by entry — illustrated against <https://github.com/mojo-molotov/ocarina-with-ai-example>:

- Server-side date bypass: covered by `Appointment - Server accepts empty date when client bypass applied`. ✓
- Past-date booking: covered. ✓
- Duplicate booking + same-day overlapping: covered. ✓
- History sort order: covered. ✓
- Profile placeholder (no editable fields): covered by `view_profile.verify_profile_has_no_form_fields`. ✓
- No CSRF token: **documented but not asserted by a test** (per the entry's status — "not currently tested for"). Candidate to surface, _unless_ the
  strategy intentionally scopes it out.
- BFcache: covered by the two post_logout tests. ✓

A documented gap intentionally without a test (behaviour the project doesn't want to assert on) should be marked as such in the spec entry; surface as
a low-priority candidate to either pin or to explicitly mark as out-of-scope in the spec.

### 6. Edge value at an input boundary

For each text-input field accepted by a form (username, password, comment, visit_date), list the standard boundaries:

- Empty (often already covered).
- Single character.
- Very long (paste-from-clipboard scale — 1 KB, 10 KB).
- Leading / trailing whitespace.
- Unicode / non-ASCII (accented characters, emoji, RTL marks).
- Special characters that _aren't_ injection payloads — apostrophe in a name (`O'Brien`), hyphen (`Mary-Jane`), etc.

**Hard filter:** drop anything that resembles an injection payload, security-attack input, or anti-feature probe. See `CLAUDE.md` → "Security testing
is functional and static — never active". If a candidate edge value looks like `' OR 1=1 --`, `<script>alert(1)</script>`, `../../../etc/passwd`, or
any other attack-shape, **do not surface it.** This skill is for functional gaps, not for injection ideas.

## Procedure

### 1. Read the strategy and the test inventory

```bash
# strategy
cat the test-strategy doc

# inventory — what currently exists
find src/tests/scenarios -name "*.py" -not -name "__init__.py"
grep -rhoE 'name=("|f")[^"]+"' src/tests/scenarios/ | sort -u
```

For a more precise inventory, parse the AST: find the adapter's `create_*_test(name=…)` calls (`create_selenium_test` / `create_playwright_test`) and
pair them with their containing file/folder.

### 2. Walk the six dimensions above

For each dimension, build a list of candidates. For each candidate:

- Name the operation / parameter / page / dispatcher path / gap / edge value.
- Cite the existing test(s) it would be adjacent to (so the reviewer sees the relationship).
- Filter through the "would a real user produce this?" lens.
- Filter through the "this is not an injection payload" lens.
- Assign a starting priority — `priority: P2` (worth raising), `P3` (informational) — flagged as the audit's guess.

### 3. Surface candidates

Use this exact template:

```markdown
# Coverage extension — candidates

## 1. Same flow, different parameter

- **Username with trailing whitespace** (P2)
  - Adjacent to: `Login - Empty Credentials`, `Login - Wrong-Case Username (lowercase)`.
  - Realistic? Yes — copy-paste from a credential manager often leaves trailing whitespace.
  - Proposed: another `failed_logins` case `("John Doe ", DEMO_PASSWORD)`.

- <next candidate>

## 2. Same operation, different page

- **Back-button BFcache from appointment page** (P2)
  - Adjacent to: `Logout - Back-button does not restore authenticated history view`.
  - Why it matters: BFcache likely behaves the same on appointment as on history, but that's an assumption — confirming it on a second protected page
    closes the assumption.
  - Proposed: new scenario `post_logout_bfcache_exposure_appointment.py` mirroring the history one, target appointment page.

## 3. Same page, different operation

- <…>

## 4. Dispatcher path uncovered

- <…>

## 5. Documented gap without test

- **No CSRF token on deployed forms** (P3 / informational)
  - Documented in the gap inventory as §G-SEC-1; the spec entry says "not currently tested for".
  - Proposed: an intentional-fail / observation test that opens the form and asserts no `<input type="hidden" name="…csrf…">` is present. **Or** an
    explicit spec note that the gap is intentionally not pinned.

## 6. Edge value at a boundary

- <…>

## Summary

- P2 candidates: N | P3 candidates: M
- Verdict: <N worth raising for review | nothing material >
```

Print the report; do not write any test. Do not create scenario files.

### 4. Stop. The user decides.

Do not write any test. Do not edit the test-strategy doc. The user reviews candidates; accepted ones go to the backlog (`manage-backlog` skill) or are
picked up directly. Many candidates _should_ be dropped — the suite shouldn't grow until every parameter has every value tried. The skill's role is
making the unmade choices visible, not making them.

## Hard filters — what this skill does NOT surface

- **Anything resembling an active security attack** — injection strings, payloads, traversal probes, token tampering. See `CLAUDE.md` → "Security
  testing is functional and static — never active". Functional security tests (CSRF presence by reading rendered HTML, server-side validation by
  submitting through the real form) are fine; attack-shape inputs are not.
- **Cases a real user could not plausibly produce.** Synthetic noise; theoretical-only boundary values; ASCII art in a username field; gigabyte-sized
  inputs.
- **Cases the strategy doc explicitly scopes out** (typical "Out of scope" categories: performance, accessibility, payment, admin interface, email/SMS
  notifications, etc.).
- **the SUT's own backlog.** Recommendations in the FRD for the SUT team to harden (e.g. `Clear-Site-Data` on logout) are not our tests to add.

## When to run this skill

- The user asks: "find coverage gaps", "what's missing from the suite", "extend the tests", "hunt for adjacent cases", "is there anything we forgot?"
- Before a release-hardening pass.
- After a SUT spec change (the FRD updated, a new requirement, a new gap discovered).
- After adding a new POM or a new page — its operations are fresh adjacent surface.

## What this skill does NOT do

- It does not write tests, scenario files, or fragments.
- It does not edit the test-strategy doc or the FRD.
- It does not silently invent edge cases — every candidate carries the "real user could produce this" filter, and is flagged with a starting priority
  for the user to confirm.
- It does not propose security/attack-shape inputs.
