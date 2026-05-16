---
name: review-intent-collisions
description: Audit pass-everywhere tests for **intent collisions** with assertive gap tests. An assertive gap test asserts that the SUT *should* reject X and is intentionally red until the SUT fixes the gap; on the day the SUT fixes it, that test flips green. A pass-everywhere test in the same perimeter must stay green **on both sides** of that fix — before the SUT enforces the rule (current state) and after (post-fix). If a happy-path test's expected outcome silently depends on the SUT's *current* buggy behaviour, it is collision-fragile: it will break when the gap is fixed and look like a regression. Use whenever the user asks to audit test robustness, find tests that aren't future-proof, review collisions with gap tests, or harden before a spec evolution. Surface candidates with concrete defensive-rewrite proposals; never edit a test.
---

# Review — intent collisions between gap tests and pass-everywhere tests

The principle. The suite ships two kinds of assertions on the same surface:

- **Assertive gap tests** — currently red by design. They encode a claim about how the SUT _should_ behave (reject past-date bookings, reject
  duplicates, render history by visit date, etc.). On the day the SUT enforces the rule, these tests flip from red to green. That transition is
  _desired_.
- **Pass-everywhere tests** — currently green. They exercise the happy path through the same surface. Their expected outcome must hold **before** the
  fix (when the SUT still has the gap) **and after** (when the SUT enforces the rule).

A collision happens when a pass-everywhere test's expected outcome silently depends on the SUT's _current_ buggy behaviour — the very behaviour the
gap test is documenting as wrong. When the SUT fixes the gap, the gap test goes green (correct), but the pass-everywhere test breaks (also correct,
_but reads as a regression_). The cause isn't a regression; it's a test that wasn't written defensively against the fix it was tacitly relying on.

This audit finds those.

The audit surfaces candidates. **It never rewrites a test.** A collision is sometimes intentional — a happy-path test that explicitly stress-tests the
current behaviour. The user decides per finding.

Default target: `src/tests/scenarios/` against the test-strategy doc §7 + the gap inventory. For a different repo, ask the user.

## The gap-test perimeter — the load-bearing dataset

For every assertive gap test, name its **perimeter** — the inputs / state the assertion fixes on the "rejected" side. A pass-everywhere test enters
the perimeter when it uses the same inputs / state. Sourced from the strategy doc each run, not hardcoded.

As a worked example, the perimeters in <https://github.com/mojo-molotov/ocarina-with-ai-example> look like this:

| Gap test                                                                    | Asserts                                                                          | Perimeter — pass-everywhere tests entering this perimeter are at risk                                                                                                                                                  |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Appointment - Past date booking accepted`                                  | the SUT _should_ reject past dates                                               | Any booking flow using `in_days(<0)`. Defensive fix: use `in_days(>0)`.                                                                                                                                                |
| `Appointment - Server accepts empty date when client bypass applied`        | the SUT _should_ reject submissions where the visit-date is empty server-side    | Any flow that strips the HTML5 `required` attr (via `bypass_visit_date_validation`) and submits expecting confirmation. Defensive fix: don't strip + submit empty unless you're the gap test.                          |
| `Appointments - Duplicate booking (same facility, date, program)`           | the SUT _should_ reject a second identical booking                               | Any flow that submits two bookings with the same `(facility, visit_date, programme)` in the same session and expects confirmation on the second. Defensive fix: vary at least one of facility / date / programme.      |
| `Appointments - Overlapping appointments (same date, different facilities)` | the SUT _should_ reject same-day bookings at different facilities                | Any flow that submits two bookings on the same `visit_date` at different facilities in the same session and expects confirmation on the second. Defensive fix: use distinct dates per facility within a session.       |
| `Journey - History ordered most-recent date first`                          | History _should_ render most-recent visit date first                             | Any flow that asserts history _order_ matches submission order rather than visit-date order — or that picks the "first card" expecting submission order. Defensive fix: assert by `visit_date` matching, not by index. |
| `Logout - Back-button does not restore authenticated history view`          | The browser _should not_ expose the authenticated view from BFcache after logout | Any flow that explicitly relies on Chrome's BFcache restoring a page (rare; none currently). Defensive fix: any test that uses `back()` post-logout must verify the destination, not assume restoration.               |
| `Logout - Session holds under back-forward stress (3 cycles)`               | Same; held under back/forward churn                                              | Same.                                                                                                                                                                                                                  |

Pull this table from your test-strategy doc (intentional gap fails + expected cross-browser reds) cross-referenced with the gap inventory each time.
New gaps automatically join the audit when they're documented.

## Procedure

### 1. Read the current gap list

```bash
sed -n '/^- \*\*Intentional gap fails/,/^- \*\*Expected/p' <path-to-test-strategy-doc>
sed -n '/^- \*\*Expected cross-browser/,/^- \*\*Under/p' <path-to-test-strategy-doc>
grep -nE "^### [A-Z]+-[A-Z]+-[0-9]+" <path-to-gap-inventory>
```

For each gap, write down its **perimeter** (one or two lines: what inputs / state put a test inside the gap's reach).

### 2. Walk every pass-everywhere test against every perimeter

Pass-everywhere tests are every scenario not in the gap list and not in the cross-browser reds. List them:

```bash
grep -rhoE 'name=("|f")[^"]+"' src/tests/scenarios/ | sort -u
```

For each pass-everywhere test, read it (or its dataset). For each gap perimeter, answer:

- **Does this test enter the perimeter?** Match by inputs (date sign, facility/date/programme tuples, history-order assumptions, BFcache reliance) or
  state (does it submit a second booking in the same session; does it strip `required`; does it rely on the browser's back-button restoring a page).
- **Does the expected outcome rely on the SUT's current behaviour?** Confirmation expected on a payload the post-fix SUT would reject = collision.
  History order asserted by submission position = collision when the fix lands.
- **Would the test still hold after the fix?** If yes, the test is robust. If no, it's collision-fragile — surface it.

### 3. Classify each finding

| Tier      | When                                                                                                                                                             |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **High**  | The test enters a gap perimeter AND its expected outcome relies on the inverse of the gap's assertion. Post-fix the test would break, looking like a regression. |
| **Maybe** | The test brushes the perimeter (e.g. uses one of the same inputs but the assertion path is on a different surface) — judgment call.                              |
| **Ok**    | The test is outside every perimeter, or the test enters a perimeter but is defensive (asserts in a way that survives the fix). Do not surface.                   |

### 4. Diagnose each High / Maybe candidate

For each candidate, name:

- The pass-everywhere test (path:line + name).
- The colliding gap (§ reference + perimeter line).
- The reliance — which specific input / state of the pass-everywhere test sits inside the perimeter.
- A concrete **defensive rewrite** — what input / assertion would make the test robust across the fix.

### 5. Report

Use this exact template:

```markdown
# Intent-collision audit — <target>

## High — pass-everywhere test collision-fragile to a gap fix

- <path>:<line> — `<test name>` collides with `<gap test name>` (gap-inventory or spec-doc reference).
  - Perimeter: <one-line — what the gap asserts the SUT should reject>.
  - Reliance: <where this test sits inside that perimeter — concrete inputs / state>.
  - Post-fix outcome: <how the test would break — "second booking would now be rejected; the verify_booking_confirmed act would fail">.
  - Defensive rewrite: <concrete change — vary the date / facility / programme; assert by date match not by index; …>.

## Maybe — judgment call

- <same shape; explicitly call out the borderline>

## Summary

- High: N | Maybe: N
- Verdict: <ship after defensive rewrites of N tests | nothing to change | …>
```

Print the report; do not write it to a file unless the user asks.

### 6. Stop. The user decides.

Defensive rewrites are sometimes the right call; sometimes the collision _is_ the test (the test is intentionally probing how the SUT behaves on this
surface and will be retired or retired-and-reframed alongside the gap fix). Hand the report over.

## Examples

### High (hypothetical, would surface if it existed)

```python
# scenario excerpt — a pass-everywhere "book twice in one session" happy path
drive_page(... submit(...))   # book #1: Tokyo, in_days(30), Medicare
drive_page(verify_booking_confirmed)   # confirmation expected
drive_page(... submit(...))   # book #2: Tokyo, in_days(30), Medicare — SAME triple
drive_page(verify_booking_confirmed)   # confirmation expected — relies on the SUT accepting duplicates
```

Collides with `Appointments - Duplicate booking (same facility, date, program)` (perimeter: same facility/date/programme twice). Post-fix, the SUT
would reject the second booking and `verify_booking_confirmed` would fail.

**Defensive rewrite**: change the second booking to use a different date or facility or programme. Example: `(Tokyo, in_days(30), Medicare)` →
`(Tokyo, in_days(31), Medicare)` — fully outside the duplicate perimeter; happy-path intent preserved.

### Ok (current `book_and_verify_history.py`)

Books one Hongkong/Medicare on `in_days(45)`, verifies in history. Single booking; no second-submit; no past-date; no submission-order assumption.
Outside every perimeter. Test stays green across every gap fix.

### Ok (current `saturation_booking.py`)

Five bookings same facility (Hongkong) on **distinct** dates (`in_days(90 + n)` for n=0..4) with the same programme. Same facility + same programme
but _different dates_ — outside the duplicate perimeter (which is same-facility-AND-same-date-AND-same-programme). Verifies every visit date is in
history by **date match**, not by position — outside the history-order perimeter. Robust.

### Maybe (current `history_ordering.py`)

This test _is_ the history-order gap test; it's not pass-everywhere. Not in scope for this audit. But it would be a good example of an _intentional_
collision were it pass-everywhere.

## When to run this skill

- The user asks: "are the tests robust to a SUT fix?", "would the suite break if the SUT fixes §X.Y?", "audit collisions", "are the happy paths
  future-proof?".
- Before signing off on a release that documents a SUT fix imminent.
- After a new gap test is added (the new gap may collide with existing happy-paths).
- After a happy-path test is added in a gap-adjacent surface (the new test may sit inside an existing perimeter).
- Before invoking `update-frd-and-tests` to mark a gap as resolved — pre-check the happy-paths in the same perimeter.

## What this skill does NOT do

- It does not rewrite any test.
- It does not flip a gap test to green. (That's the `update-frd-and-tests` skill's territory, and only on confirmed resolution.)
- It does not invent gap perimeters that aren't documented. The perimeter table is read from the strategy doc and the gaps file; if a gap isn't listed
  there, it isn't audited here.
- It does not surface a test as "fragile" just because it touches the same surface as a gap. The reliance test is concrete: does the _expected
  outcome_ depend on the SUT's _current_ behaviour? If not — robust.
