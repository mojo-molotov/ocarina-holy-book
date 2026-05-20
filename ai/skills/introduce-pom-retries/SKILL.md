---
name: introduce-pom-retries
description:
  "**Anti-flakiness skill for introducing retries *inside POM methods*** — distinct from the Ocarina test-life retry budget that wraps the whole test,
  this is finer-grained: a single POM operation (login click, form submit, page-load wait) gets a **separate `_with_retries` wrapper method** that
  re-attempts it N times, while the idempotent base method stays untouched — the established `ocarina-example` pattern. The skill surfaces candidate
  POM methods whose flake signature suggests in-method retry treatment (same operation fails intermittently with the same inputs, succeeds after a
  short delay) and recommends the **two-test split** discipline: when a POM operation needs a retry to be reliable, that's a flake demonstration —
  split the test into a *first-try* variant (no retries, intentional fail until the SUT is fixed; keeps pressure on the team) and a *with-retries*
  variant (passes via the wrapper; keeps coverage stable while waiting for the fix). The base operation method must be **idempotent** — it clears its
  own fields and dismisses its own overlays each call, since nothing guarantees the SUT resets between attempts and Selenium's `send_keys` appends
  rather than replaces; the wrapper just re-calls it. The machine never decides to add retries unilaterally — it observes the signature and proposes;
  the user signs off. Use whenever the user asks to add POM retries, audit POM methods for flake signatures, plan a retry-and-split refactor, or
  harden a specific POM operation that's been flaking."
---

# Introduce POM retries — and split the test in two to prove the flake

A flakiness-mitigation skill. Ocarina has two retry layers already: the test-life budget (retry the _whole test_) and the transient-error classifier
(which exceptions are retryable). This skill adds a third, finer-grained layer:

> _A separate `_with_retries` wrapper method re-attempts a POM operation N times before surrendering — bounded by a wait, with a count, observable in
> logs._

The philosophy from `CLAUDE.md` and the project's discipline:

- We don't fail a test on a transient symptom that a real user would never notice.
- When a POM operation needs internal retries to be reliable, that _is_ a flake — and a flake should be **demonstrated**, not buried.

So the discipline isn't _"add retries and move on"_. It's:

1. **Add a `_with_retries` wrapper method beside the POM operation** — so the flake stops killing coverage.
2. **Split the affected test into two**:
   - A **first-try** variant that calls the **base operation method** directly (no retries). This test is an **intentional fail** until the SUT is
     fixed. It keeps the bug visible in the report; the team sees it every run.
   - A **with-retries** variant that calls the **`_with_retries` wrapper**. This test passes; the suite stays useful as coverage while the SUT defect
     waits to be fixed.

Together, the pair definitively proves the flake exists _and_ keeps coverage usable. Once the SUT is fixed, the first-try test starts passing and the
team can either delete the split (merge back) or keep both as regression guards.

## The flake signature that justifies POM retries

POM retries are not a fix-all. They're appropriate for a narrow signature:

- **Same operation, same inputs**, repeated within a short window (seconds), succeeds intermittently — not deterministically.
- The failure is **observable but transient** — a `TimeoutException`, a `StaleElementReferenceException`, a click that doesn't take effect on first
  try.
- The retry **with the exact same call** succeeds; no input change, no environmental fix needed.
- The flake **is not explained by a known environment artifact** (cross-check against `the gap inventory (environmental section)`). If `§A-ENV-1`
  rapid-POST contention explains it, the fix is environmental, not POM-level.
- The flake **is not explained by a missing wait condition**. If the operation reliably succeeds after adding a `wait_for(...)`, the fix is the wait,
  not a retry loop. _Retries are for when waits don't help_ — the operation needs to be _re-attempted_, not just waited on.

If any of these checks fail, the POM-retry treatment is the wrong tool. The skill surfaces the cross-reference and stops.

## The retry shape — a separate `_with_retries` wrapper method

**Do not add a `retries` parameter to the operation.** Keep the base operation method exactly as it is and add a **separate wrapper method** beside it
that calls the base method in a loop. This is the established `ocarina-example` pattern — see `DashboardLoginPage.login_without_otp` +
`login_without_otp_and_with_retries`, `CorsicamonPage.enter_fresh_corsicamon_id` + `enter_fresh_corsicamon_id_with_retries`, `ChaoticFormPage`'s
`_fill_form_and_send_it` + `fill_form_and_send_it_with_retries` in <https://github.com/mojo-molotov/ocarina-example>.

Two methods, two responsibilities:

**The base operation method — unchanged, single attempt, self-resetting.** It performs the operation once and is _idempotent_: it resets its own
preconditions every call. `login_without_otp` does `username_input.clear()` then `send_keys(...)`, and the same for the password — so re-invoking it
is always a clean fill, never a doubled one. This is where the "reset between retries" discipline lives: not in the loop, but in a base method written
so that _calling it again is calling it fresh_. Give the base method a `skip_check: bool = False` parameter so the wrapper can ask it to skip its own
success-verification (the wrapper runs its own).

**The wrapper method — `<operation>_with_retries`, the loop.** A separate, additive method. It validates the retry count, calls the base method,
checks for success, and re-attempts on failure (helpers below — `validate` / `is_positive`, `take_screenshot`, `get_timeout`, `suppress` — are the
`ocarina-example` equivalents; use your project's):

```python
def login_without_otp_and_with_retries(
    self, creds: ImmutableCredentials, retries: int, *, logger: ILogger,
) -> DashboardLoginPage:
    """Fill creds and click the login btn (n retries)."""
    validate(retries, name="retries").assert_that(is_positive).execute().raise_if_invalid()

    attempts_count = 1
    while attempts_count <= retries:
        self.login_without_otp(creds)          # base method — self-resetting, clean each call
        with suppress(Exception):
            WebDriverWait(self._driver, get_timeout()).until(
                ec.invisibility_of_element_located(self._password_input)
            )
            break                              # success — the login form is gone
        logger.warning(
            f"Failed to connect to the dashboard, without OTP.\n"
            f"Life: {attempts_count}/{retries}\n"
            f"Current URL: {self._driver.current_url}"
        )
        take_screenshot(driver=self._driver, logger=logger, category="WARNING")
        attempts_count += 1

    s = "s" if attempts_count > 1 else ""
    logger.info(f"Connected to the dashboard, without OTP. After {attempts_count} attempt{s}.")
    return self
```

Properties of the wrapper, each load-bearing:

- **It is a separate method, not a parameter.** The base method's signature and every existing call site stay untouched — the wrapper is purely
  additive. A `retries=0` default would still widen the base method's surface and invite callers to thread a count through it.
- **`retries` is validated, not defaulted.** `validate(retries, name="retries").assert_that(is_positive)` — the wrapper exists _to_ retry, so a
  non-positive count is a caller error, not a silent single-attempt.
- **Success is an observed condition, not an absent exception.** `with suppress(Exception): WebDriverWait(...).until(<success condition>); break` —
  the loop stops only when the success condition is _seen_ (the password field gone, the draw-complete message up, …). Real errors from the base
  operation still bubble out of the wrapper.
- **Every failed attempt warns and takes a `WARNING`-category screenshot.** `logger.warning(...)` with `Life: N/retries` and the current URL, plus
  `take_screenshot(..., category="WARNING")`. The warning trail and the shots are the empirical evidence the flake exists — the same evidence the
  two-test split rests on.
- **Re-arming between attempts lives in the wrapper.** When the base method alone cannot get back to a retryable state — a network-error panel whose
  "retry" button must be clicked first — the wrapper does that between attempts (see `make_a_new_draw_with_retries`, which calls a nested
  `_click_retry_button()` before looping). The base method resets _its_ inputs; the wrapper resets anything _around_ the operation.
- **It returns `self`** so it chains in scenarios like any other POM method, and a closing `logger.info("... After N attempt(s).")` records how many
  attempts success took.

### Naming

Suffix the base method's name with `_with_retries` — `enter_api_key` → `enter_api_key_with_retries`, `type_otp` → `type_otp_with_retries`. When the
base name already carries a clause, insert `and` so it still reads — `login_without_otp` → `login_without_otp_and_with_retries`. The name must make
the pair obvious: a reader scanning the POM sees the base operation and its retrying sibling side by side.

## The base method must be idempotent — that is the reset discipline

A retry is only safe if calling the base operation again is the same as calling it the first time. **Nothing guarantees the SUT or the page clears
state between attempts** — Selenium's `send_keys` _appends_, so a base method that does not `clear()` first submits `JohnDoeJohnDoe` on the second
call and fails for a reason that has nothing to do with the original flake. So the base operation method must reset its own preconditions, every call:

- **Text inputs** — `element.clear()` before every `send_keys`, exactly as `login_without_otp` and `enter_fresh_corsicamon_id` do.
- **Widget-decorated inputs** — re-set the backing field through the widget's API (per the _widget-decorated inputs_ rule in `CLAUDE.md`); a leftover
  datepicker calendar or autocomplete dropdown intercepts the next call.
- **Overlays / modals / flash errors** — dismiss anything a prior call surfaced (a validation banner, a "fields required" toast) so it does not
  intercept clicks or mislead the success check.
- **Page-level operations** — re-`get()` the page URL if a prior call navigated partway, so the operation starts from its documented entry point.

If the base method _cannot_ be made idempotent on its own — the SUT requires an explicit "retry" action to return to a retryable state — that
re-arming step belongs in the wrapper, between attempts, not in the base method. The base method resets its own inputs; the wrapper resets the
surrounding state. Either way, **no attempt ever runs on top of the wreckage of the last one** — that is the rule; the wrapper pattern is just where
`ocarina-example` puts each half of it.

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
- Not explained by `the gap inventory (environmental section)`?
- Not solvable by adding a wait condition instead?

If all five → candidate. If any one fails → not a POM-retry case; surface the cross-reference to the better tool (environment fix, wait condition,
test redesign).

### Step 3 — Cross-check with run history

For each candidate, look at recent run reports (`pick-reports`) / logs (`pick-logs`):

- How often did the POM operation fail intermittently?
- Did the test-life budget catch it (i.e., the _whole test_ re-ran successfully)?
- Is the test currently classified as `Pass everywhere` in the test-strategy doc, or already flagged as flaky?

If the test-life budget is consistently absorbing the flake, POM-level retries may be unnecessary — the existing layer is doing its job. Surface the
question.

### Step 4 — Recommend the two-test split (per candidate where the flake is real)

For each confirmed candidate:

- **First-try variant**: existing test renamed / cloned, calling the **base operation method** directly (e.g. `login_without_otp`). This becomes an
  intentional fail. Filed in the test-strategy doc under intentional-gap-fails; filed in the gap inventory with the flake description and the observed
  signature.
- **With-retries variant**: existing test (or new sibling), calling the **`_with_retries` wrapper** with an explicit `retries=N`. The N is the user's
  call — start with 1 or 2; if more is needed, the flake is severe enough to surface differently (probably a SUT bug worth filing in its own right).

Name the split clearly: `<original test name>` becomes `<original test name> (first-try)` and `<original test name> (with-retries)`. The first-try
variant's test name reads as a question to the SUT team: _"the SUT should accept this on first try"_.

### Step 5 — Surface the catalogue

```markdown
# POM-retry candidates — <project-name> (<date>)

## Candidates

### `<page>.<method>` at `<file>:<line>`

- **Flake signature**: <one-sentence description with empirical evidence — log line counts, exception classes>.
- **Five-question checklist**: same op same inputs ✓ | observable transient ✓ | retry succeeds ✓ | not env artifact ✓ | not waitable ✓.
- **Currently absorbing layer**: <test-life budget masks it / no current absorption>.
- **Cross-reference**: `the gap inventory <entry-ref>` if matches | new flake to file.
- **Proposed retry shape**: new wrapper method `<page>.<method>_with_retries(...)` beside the base method; `retries: int` validated positive; success
  condition `<the observable that ends the loop>`; base-method idempotency `<what the base method must clear each call>`; wrapper re-arming
  `<extra step between attempts, if any — e.g. a network-error retry-button click>`.
- **Two-test split**:
  - First-try variant: `<test name (first-try)>` — calls the base method directly, intentional fail, file in the test-strategy doc, log in the gap
    inventory under a new entry-ref.
  - With-retries variant: `<test name (with-retries)>` — calls `<method>_with_retries(retries=<N>)`, expected pass, file in the test-strategy doc as
    `Pass everywhere` (or per the policy).
- **Closure trigger**: when SUT is fixed, the first-try variant starts passing → merge the split (or keep both as regression guards, user's call).

## Not POM-retry candidates (cross-reference)

- `<method>`: flake is `§A-ENV-1` rapid-POST contention — environmental, not POM-fixable.
- `<method>`: flake is solved by adding a wait condition; no retry loop needed.
- `<method>`: test-life budget already absorbs cleanly — no new layer needed.

## Cross-references

- `src/lib/errors.py` (transient classification — the existing retry layer).
- Ocarina test-life budget — the wrap-the-whole-test layer.
- `the gap inventory (environmental section)` — environment artifacts (rule out before recommending POM retries).
- Sister skills: `analyse-flakiness` (transient classifier widening), `analyse-fixture-flakiness` (boundary instrumentation),
  `understand-sut-constraints` (when the flake is a SUT bound).

## Recommended next motions

- For each candidate: a refactor PR per POM method (or one PR per page if changes are tightly coupled). The skill describes the move; the user authors
  the implementation and the two-test split.
- For each "not POM-retry" cross-reference: the linked motion (env fix / wait addition / no change).
- For each two-test split: update the test-strategy doc categories and the gap inventory entries via `update-frd-and-tests`.

## Verdict

<one-line: N candidates worth POM retries with two-test split, K cross-referenced elsewhere, nothing material>.
```

Print the catalogue.

### Step 6 — Stop. The user decides.

Each candidate resolves as:

- **Retry + split** — the user (or follow-up edit motion) adds the `_with_retries` wrapper method beside the base operation and creates the two-test
  split.
- **Retry without split** — discouraged but allowed if the user explicitly waives the demonstration discipline. Surface the trade-off (silence the
  flake from the report at the cost of losing pressure on the SUT team).
- **Defer** — record for the next stability pass.
- **Reject** — flake doesn't fit the POM-retry signature; pursue the cross-referenced motion instead.

## Hard rules

- **Five-question checklist is non-negotiable.** A POM retry that doesn't pass the checklist is hiding a problem rather than handling one.
- **Two-test split is the philosophy.** Adding retries without splitting silences the flake and loses pressure on the SUT team. The split keeps both
  benefits.
- **The retry is a separate wrapper method, not a parameter.** `<operation>_with_retries` sits beside the base method and calls it in a loop. The base
  method's signature and call sites are never touched — the wrapper is purely additive. This is the `ocarina-example` pattern.
- **The base operation method must be idempotent.** Every retry re-calls it, so it resets its own preconditions each call (`clear()` before
  `send_keys`, re-set widgets, dismiss its own leftovers). `send_keys` appends — a base method without `clear()` submits doubled input on the second
  call. Re-arming the SUT needs _around_ the operation (a network-error "retry" button) belongs in the wrapper, between attempts.
- **`retries` is validated, not defaulted.** The wrapper exists to retry; assert a positive count (`validate(retries).assert_that(is_positive)` in
  `ocarina-example`) rather than letting a zero silently mean "single attempt".
- **Re-attempt is outcome-driven.** The loop breaks when the success condition is _observed_ (the form gone, the draw complete), not when a particular
  exception was caught. Real errors from the base operation still bubble.
- **Every failed attempt warns and screenshots.** `logger.warning(...)` with `Life: N/retries` + current URL, and a `WARNING`-category screenshot.
  That trail is the empirical evidence the flake exists — the two-test split rests on it.
- **Cross-check the environmental section of the gap inventory before recommending.** Environment artifacts are not POM-fixable.
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
- It does not author the two-test split's test names or the test-strategy doc / the gap inventory updates. Recommends the shape; the user (via
  `update-frd-and-tests`) applies.
- It does not run the suite to validate the retry shape. Verification is the user's motion.
- It does not modify Ocarina internals (the test-life budget, the transient classifier). Those layers are out of scope; this skill stays at the POM
  layer.
- It does not include attack-shape retries. Per `CLAUDE.md`.
