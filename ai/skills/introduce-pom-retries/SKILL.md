---
name: introduce-pom-retries
description:
  "**Anti-flakiness skill for introducing retries *inside POM methods*** — distinct from the Ocarina test-life retry budget that wraps the whole test,
  this is finer-grained: a single POM operation (login click, form submit, page-load wait) retries N times internally before bubbling failure. The
  skill surfaces candidate POM methods whose flake signature suggests in-method retry treatment (same operation fails intermittently with the same
  inputs, succeeds after a short delay) and recommends the **two-test split** discipline: when a POM operation needs a retry to be reliable, that's a
  flake demonstration — split the test into a *first-try* variant (no retries, intentional fail until the SUT is fixed; keeps pressure on the team)
  and a *with-retries* variant (passes via POM retries; keeps coverage stable while waiting for the fix). The machine never decides to add retries
  unilaterally — it observes the signature and proposes; the user signs off. Use whenever the user asks to add POM retries, audit POM methods for
  flake signatures, plan a retry-and-split refactor, or harden a specific POM operation that's been flaking."
---

# Introduce POM retries — and split the test in two to prove the flake

A flakiness-mitigation skill. Ocarina has two retry layers already: the test-life budget (retry the _whole test_) and the transient-error classifier
(which exceptions are retryable). This skill adds a third, finer-grained layer:

> _Inside a POM method, the operation itself retries N times before surrendering — bounded by a wait, with a count, observable in logs._

The philosophy from `CLAUDE.md` and the project's discipline:

- We don't fail a test on a transient symptom that a real user would never notice.
- When a POM operation needs internal retries to be reliable, that _is_ a flake — and a flake should be **demonstrated**, not buried.

So the discipline isn't _"add retries and move on"_. It's:

1. **Add retries inside the POM** — so the flake stops killing coverage.
2. **Split the affected test into two**:
   - A **first-try** variant that calls the POM operation in a _no-retry_ mode. This test is an **intentional fail** until the SUT is fixed. It keeps
     the bug visible in the report; the team sees it every run.
   - A **with-retries** variant that uses the normal POM operation (which now retries internally). This test passes; the suite stays useful as
     coverage while the SUT defect waits to be fixed.

Together, the pair definitively proves the flake exists _and_ keeps coverage usable. Once the SUT is fixed, the first-try test starts passing and the
team can either delete the split (merge back) or keep both as regression guards.

## The flake signature that justifies POM retries

POM retries are not a fix-all. They're appropriate for a narrow signature:

- **Same operation, same inputs**, repeated within a short window (seconds), succeeds intermittently — not deterministically.
- The failure is **observable but transient** — a `TimeoutException`, a `StaleElementReferenceException`, a click that doesn't take effect on first
  try.
- The retry **with the exact same call** succeeds; no input change, no environmental fix needed.
- The flake **is not explained by a known environment artifact** (cross-check against `IDENTIFIED_GAPS.md §A-ENV-*`). If `§A-ENV-1` rapid-POST
  contention explains it, the fix is environmental, not POM-level.
- The flake **is not explained by a missing wait condition**. If the operation reliably succeeds after adding a `wait_for(...)`, the fix is the wait,
  not a retry loop. _Retries are for when waits don't help_ — the operation needs to be _re-attempted_, not just waited on.

If any of these checks fail, the POM-retry treatment is the wrong tool. The skill surfaces the cross-reference and stops.

## The retry shape inside the POM

A standard POM-retry method (proposed, not authoritative — the user shapes the actual implementation):

```python
def login(self, username: str, password: str, *, retries: int = 0) -> None:
    """Log in. With retries=0 (default), single attempt. With retries=N, retry up to N times."""
    attempts = retries + 1
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            # the operation
            return
        except (TimeoutException, StaleElementReferenceException) as exc:
            last_exc = exc
            self._logger.warning(f"login attempt {attempt}/{attempts} failed: {exc}")
            time.sleep(_RETRY_BACKOFF)
    raise last_exc  # exhausted
```

The shape has four important properties:

- **`retries=0` is the default** so existing call sites don't change behaviour silently.
- **Each attempt logs** so the report shows the retry count — empirical evidence of the flake.
- **The exception types are explicit** (no broad `except Exception`) — only known-transient symptoms retry; real errors bubble.
- **Backoff is a named constant** in `src/constants/` (per the compartmentalisation discipline).
- **Exhaustion raises the last exception** so the test-life budget still gets a chance to retry the whole test.

## Procedure

### Step 1 — Inventory the candidate POM methods

```bash
grep -rn "def " src/pages --include="*.py" | grep -v "^.*:[^:]*:def __"
```

For each method, note: what operation it performs, what exceptions it can raise, whether its flake history is observable in logs / reports.

### Step 2 — Walk the flake signature checklist per candidate

For each method, walk the five-question signature:

- Same operation, same inputs, intermittent failure?
- Failure observable but transient (`TimeoutException` / `StaleElementReferenceException` / silent no-op)?
- Retry with the exact same call succeeds?
- Not explained by `IDENTIFIED_GAPS.md §A-ENV-*`?
- Not solvable by adding a wait condition instead?

If all five → candidate. If any one fails → not a POM-retry case; surface the cross-reference to the better tool (environment fix, wait condition,
test redesign).

### Step 3 — Cross-check with run history

For each candidate, look at recent run reports (`pick-reports`) / logs (`pick-logs`):

- How often did the POM operation fail intermittently?
- Did the test-life budget catch it (i.e., the _whole test_ re-ran successfully)?
- Is the test currently classified as `Pass everywhere` in `CURA_TEST_STRATEGY.md §7`, or already flagged as flaky?

If the test-life budget is consistently absorbing the flake, POM-level retries may be unnecessary — the existing layer is doing its job. Surface the
question.

### Step 4 — Recommend the two-test split (per candidate where the flake is real)

For each confirmed candidate:

- **First-try variant**: existing test renamed / cloned, calling the POM operation with `retries=0`. This becomes an intentional fail. Filed in
  `CURA_TEST_STRATEGY.md §7` under intentional-gap-fails; filed in `IDENTIFIED_GAPS.md` with the flake description and the observed signature.
- **With-retries variant**: existing test (or new sibling), calling the POM operation with `retries=N` for an explicit N. The N is the user's call —
  start with 1 or 2; if more is needed, the flake is severe enough to surface differently (probably a SUT bug worth filing in its own right).

Name the split clearly: `<original test name>` becomes `<original test name> (first-try)` and `<original test name> (with-retries)`. The first-try
variant's test name reads as a question to the SUT team: _"the SUT should accept this on first try"_.

### Step 5 — Surface the catalogue

```markdown
# POM-retry candidates — the project root (<date>)

## Candidates

### `<page>.<method>` at `<file>:<line>`

- **Flake signature**: <one-sentence description with empirical evidence — log line counts, exception classes>.
- **Five-question checklist**: same op same inputs ✓ | observable transient ✓ | retry succeeds ✓ | not env artifact ✓ | not waitable ✓.
- **Currently absorbing layer**: <test-life budget masks it / no current absorption>.
- **Cross-reference**: `IDENTIFIED_GAPS.md §<ref>` if matches | new flake to file.
- **Proposed retry shape**: `retries: int = 0` parameter, types `<list>` retryable, backoff `<seconds>` from new constant `<name>` in
  `src/constants/<file>.py`.
- **Two-test split**:
  - First-try variant: `<test name (first-try)>` — `retries=0`, intentional fail, file in `CURA_TEST_STRATEGY.md §7`, log in `IDENTIFIED_GAPS.md` as
    `<G-X.Y>`.
  - With-retries variant: `<test name (with-retries)>` — `retries=<N>`, expected pass, file in §7 as `Pass everywhere` (or per the policy).
- **Closure trigger**: when SUT is fixed, the first-try variant starts passing → merge the split (or keep both as regression guards, user's call).

## Not POM-retry candidates (cross-reference)

- `<method>`: flake is `§A-ENV-1` rapid-POST contention — environmental, not POM-fixable.
- `<method>`: flake is solved by adding a wait condition; no retry loop needed.
- `<method>`: test-life budget already absorbs cleanly — no new layer needed.

## Cross-references

- `src/lib/errors.py` (transient classification — the existing retry layer).
- Ocarina test-life budget — the wrap-the-whole-test layer.
- `IDENTIFIED_GAPS.md §A-ENV-*` — environment artifacts (rule out before recommending POM retries).
- Sister skills: `analyse-flakiness` (transient classifier widening), `analyse-fixture-flakiness` (boundary instrumentation),
  `understand-sut-constraints` (when the flake is a SUT bound).

## Recommended next motions

- For each candidate: a refactor PR per POM method (or one PR per page if changes are tightly coupled). The skill describes the move; the user authors
  the implementation and the two-test split.
- For each "not POM-retry" cross-reference: the linked motion (env fix / wait addition / no change).
- For each two-test split: update `CURA_TEST_STRATEGY.md §7` categories and `IDENTIFIED_GAPS.md` entries via `update-frd-and-tests`.

## Verdict

<one-line: N candidates worth POM retries with two-test split, K cross-referenced elsewhere, nothing material>.
```

Print the catalogue.

### Step 6 — Stop. The user decides.

Each candidate resolves as:

- **Retry + split** — the user (or follow-up edit motion) adds the `retries` parameter to the POM method and creates the two-test split.
- **Retry without split** — discouraged but allowed if the user explicitly waives the demonstration discipline. Surface the trade-off (silence the
  flake from the report at the cost of losing pressure on the SUT team).
- **Defer** — record for the next stability pass.
- **Reject** — flake doesn't fit the POM-retry signature; pursue the cross-referenced motion instead.

## Hard rules

- **Five-question checklist is non-negotiable.** A POM retry that doesn't pass the checklist is hiding a problem rather than handling one.
- **Two-test split is the philosophy.** Adding retries without splitting silences the flake and loses pressure on the SUT team. The split keeps both
  benefits.
- **`retries=0` default.** Existing call sites must not change behaviour silently. The retry behaviour is opt-in.
- **Explicit exception types.** No `except Exception`. Each retryable type is named.
- **Backoff is a named constant.** Per the compartmentalisation discipline; no magic numbers.
- **Log every attempt.** The retry count is the empirical evidence of the flake; without it, the split is unjustified.
- **Cross-check `§A-ENV-*` before recommending.** Environment artifacts are not POM-fixable.
- **Static review only.** The skill surfaces; the user applies. The retry implementation is authoring data — per the project's discipline.
- **The N (retry count) is the user's call.** The skill suggests 1 or 2; the user picks. A POM that needs 5+ retries to be reliable is surfacing a SUT
  defect worth filing separately, not a tuning question.
- **When the SUT is fixed, the split should be revisited.** The first-try variant starts passing → merge back, or keep both as regression guards.
  Don't leave intentional-fail tests lying around once the gap is closed.
- **Per `CLAUDE.md`: security testing is functional and static — never active.** This skill respects the line.

## When to run this skill

- After a `review-suite-stability` audit surfaces a POM operation flaking with a consistent signature.
- When a test-life budget consistently catches a specific POM operation's flake — the retry could move down a layer for less wasted re-run.
- When a contributor proposes adding retries somewhere — vet against the checklist before merging.
- During flakiness-investigation sessions paired with `analyse-flakiness` / `analyse-fixture-flakiness`.
- After a SUT change that introduced new transient behaviour.

## What this skill does NOT do

- It does not modify any POM. Surfaces; user applies.
- It does not unilaterally add retries to suppress flakes. The two-test split is the philosophy — silencing without demonstrating is rejected.
- It does not pick the retry count N. Suggests 1 or 2; user decides.
- It does not author the two-test split's test names or the `CURA_TEST_STRATEGY.md` / `IDENTIFIED_GAPS.md` updates. Recommends the shape; the user
  (via `update-frd-and-tests`) applies.
- It does not run the suite to validate the retry shape. Verification is the user's motion.
- It does not modify Ocarina internals (the test-life budget, the transient classifier). Those layers are out of scope; this skill stays at the POM
  layer.
- It does not include attack-shape retries. Per `CLAUDE.md`.
