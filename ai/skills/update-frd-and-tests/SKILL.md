---
name: update-frd-and-tests
description:
  Workflow for updating an item in `CURA_FRD.md` (a REQ, a §9 gap, an element ID, a business rule) and propagating the change to every affected POM,
  connector, scenario, the test-strategy doc, and `IDENTIFIED_GAPS.md` — verifying empirically before writing any new assertion, and never silently
  flipping a gap test green when CURA appears to have fixed something. Plan first, surface for review (the changes are authoring data), then apply per
  the user's sign-off. Use whenever the user asks to update the FRD, amend a requirement, mark a §9 gap resolved, change an element ID, or adapt tests
  after a CURA spec change. Never auto-apply; never "fix" a §9 gap test to green without explicit gap-resolution evidence and an FRD/GAPS update.
---

# Update an FRD item and adapt the affected tests

A workflow skill for when the spec changes — either because the user is amending a requirement, or because CURA's actual behaviour drifted from what
the FRD asserts and the FRD needs to catch up. The skill walks the change end-to-end: spec → empirical verification → affected artifacts → proposed
updates → review → apply → strategy/gaps reconciliation.

The discipline:

- **The FRD is the spec.** Update it first, deliberately, with a one-sentence reason for the change.
- **Verify empirically before adapting any assertion.** Don't rewrite a test against the new claim until a probe / source read / live HTML confirms
  it.
- **Never silently flip a gap test to green.** If the FRD change marks a §9 gap as resolved, the corresponding intentional-fail test does **not**
  disappear — it stays as a regression guard, reframed from "intentional fail" to "passing test". The user signs off on this transition explicitly.
- **Authoring data needs review.** Every proposed change to a POM selector, connector, scenario assertion, or strategy entry is surfaced as a plan
  before any file is touched (per `CLAUDE.md` → "Datasets are authoring decisions").

Default targets: `CURA_FRD.md`, `CURA_TEST_STRATEGY.md`, `IDENTIFIED_GAPS.md`, `src/`. For a different repo, ask the user.

## Procedure

### Step 1 — State the change in one sentence

"REQ-AUTH-2 now requires the session cookie to be expired on logout, not just the server-side session destroyed (CURA fixed §9.10 in deployment Y)."
Or: "REQ-APPT-3 visit-date input ID renamed from `txt_visit_date` to `txt-visit-date`." Or: "§9.7 (past-date booking accepted) resolved — CURA now
rejects past dates server-side."

The one-sentence form forces clarity. Bigger changes split into multiple invocations.

### Step 2 — Update the FRD entry

Apply the change to the relevant section of `CURA_FRD.md` — the REQ definition, the §9 entry, the element ID in the form table, the business rule. Add
a one-line revision note in §11 ("Document Revision History").

This is the spec moving. Apply it before touching tests. The tests adapt to the spec, not the other way around.

### Step 3 — Empirically verify the new claim

Per the `empiricism` skill: every load-bearing claim in the new FRD entry must come from observation, not assumption. Pick a verification path:

- **PHP read** — `gh api repos/katalon-studio/katalon-demo-cura/contents/<file>.php` for server-side behaviour.
- **Live HTML read** — a throwaway probe that captures `outerHTML` for the affected element/page.
- **Cookies / headers** — a `curl -v` probe for session lifecycle.
- **End-to-end probe** — drive the exact flow and observe.

Record the empirical answer in the FRD entry itself (a line like "verified against the deployed app on YYYY-MM-DD: cookie expiry observed via
`driver.get_cookies()` post-logout"). The probe is throwaway; the _finding_ lives in the spec.

If verification fails or is indeterminate, stop. Don't propagate a claim you couldn't confirm.

### Step 4 — Find every artifact the change touches

Grep for the changed REQ ID, element ID, §9.x number, business-rule keyword, and the symbols those imply:

```bash
# Element ID change — find selectors using it
grep -rn "txt_visit_date" src
grep -rn "txt-visit-date" src

# REQ change — find scenarios / strategy entries referencing it
grep -rn "REQ-AUTH-2" the project root
grep -rn "§9.10" the project root

# §9 gap resolved — find the corresponding intentional-fail test
grep -rn "name=\".*Past date booking" src/tests/scenarios

# Selector text changed — find locators
grep -rn "No appointment\." src/pages
```

Build the affected-artifacts list:

| Artifact class    | Where to look                                                                                              |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| POM selectors     | `src/pages/**/*.py` — `_xxx = (By.…, "...")` lines                                                         |
| POM method bodies | `src/pages/**/*.py` — any `find_element` / `execute_script` mentioning the element                         |
| Connectors        | `src/lib/connectors/test_steps/**/*.py` — methods wrapping affected POM operations                         |
| Scenarios         | `src/tests/scenarios/**/*.py` — flows asserting against the changed surface                                |
| Datasets          | `src/tests/scenarios/**/datasets/**/*.py`, inline `*_cases` tuples                                         |
| Strategy doc      | `CURA_TEST_STRATEGY.md` §5 (coverage tables), §6 (tree), §7 (expected outcome categories), §8 (known gaps) |
| Gaps doc          | `IDENTIFIED_GAPS.md` — entries citing the changed area                                                     |

Classify each hit:

- **Affected** — the change requires editing this hit.
- **Incidental** — the hit mentions the changed area but the test isn't asserting on the changed surface. Don't touch.

### Step 5 — Special handling for §9 gap resolution

If the FRD change is **"CURA fixed a gap" / "§9.x resolved"**, the intentional-fail test against that gap is special:

1. **Do not delete it.** It stays as a regression guard.
2. **Do not silently flip its assertions.** A flipped assertion that passes for the wrong reason (e.g. §A-ENV-1 transport flake mimicking rejection)
   is exactly the trap the original misdiagnosis-prevention rules guard against.
3. **Walk the resolution evidence with the user.** Did CURA actually fix it? When was the fix observed? Is the fix server-side, deployment-specific,
   or behind a feature flag?
4. If the resolution is confirmed:
   - **Reframe the test** — change the assertion from "must NOT confirm" to "must confirm" (or the appropriate inversion). The test name should also
     flip: e.g. `Appointment - Past date booking accepted` → `Appointment - Past date booking rejected`. **Surface this rename for the user.**
   - **Move it in `CURA_TEST_STRATEGY.md`** — from the "Intentional gap fails" category in §7 to the "Pass everywhere" category. Update the §5 row's
     "Type" column from "Business attack" / **INTENTIONAL FAIL** to "Happy path" / PASS or similar. Update §8 (known gaps table) — remove the row.
   - **Update `IDENTIFIED_GAPS.md`** — mark the entry resolved (or remove it, citing the resolution date and the PR / deployment that fixed it).
5. **If the resolution is NOT confirmed** (probe shows the gap is still real on deployment): the FRD update was premature; back it out or mark
   provisional.

Same logic for the documented cross-browser reds (`§B-BROWSER-1`, the BFcache pair). If Chrome's BFcache behaviour changed (a Chrome version stops
admitting `no-store` pages), apply the same reframing path.

### Step 6 — Propose the plan

Surface, file by file, what you intend to change. Use this exact template:

```markdown
# FRD-update plan — <one-sentence change>

## FRD (`CURA_FRD.md`)

- §<X.Y> — <before> → <after>. Reason: <one line>.
- §11 — revision history: `| 1.N | YYYY-MM-DD | … | <change summary> |`.

## Empirical verification

- <claim 1>: <how verified — PHP file/line, probe finding>
- <claim 2>: …

## Affected artifacts

### POMs

- `src/pages/<file>.py:<line>` — selector / method body — <before> → <after>.

### Connectors

- `src/lib/connectors/test_steps/<file>.py:<line>` — <change>.

### Scenarios

- `src/tests/scenarios/<file>.py:<line>` — assertion / flow — <change>. Category: <pass-everywhere / intentional-fail being reframed / etc.>

### `CURA_TEST_STRATEGY.md`

- §5 row: <before> → <after>.
- §7 category: <move / unchanged>.
- §8 known gaps: <remove row / add row / unchanged>.

### `IDENTIFIED_GAPS.md`

- §<entry>: <mark resolved / remove / amend>.

## Reframings (gap tests changing status)

- `<test name>` — was Intentional FAIL (§9.X). Now: <happy path / new framing / removed?>.
  - Resolution evidence: <link to probe finding>.
  - Proposed rename: `<old name>` → `<new name>`.
```

Print the plan. Wait for the user's go.

### Step 7 — Apply approved changes

Once the user signs off:

1. Apply FRD updates first.
2. Apply POM / connector / scenario updates.
3. Apply strategy doc and gaps updates.
4. Run `ruff format && ruff check && mypy` — clean any fallout.
5. Run the affected scenarios on both browsers. The outcome should match the new expected category (the reframed gap test now passes; pass-everywhere
   tests still pass; etc.).

Do not commit. Surface the diff to the user — they commit when ready (or invoke the `pr-report` skill).

### Step 8 — Stop

Do not iterate without the user. Do not "go on" to neighbouring changes the audit happens to spot. One FRD change at a time.

## What this skill never does

- It never flips an intentional-fail test to green without explicit resolution evidence and the full reframing pass (FRD, GAPS, strategy, test
  rename).
- It never deletes a test that was previously an intentional-fail gap test. They stay as regression guards, reframed.
- It never silently propagates a CURA-side change. The FRD update is deliberate and visible.
- It never invents an empirical answer. If verification is indeterminate, the workflow stops.
- It never updates the strategy doc's pass/fail counts — there are none (per the §7 "no totals" rule). It updates _categories_.

## When to run this skill

- The user announces a CURA spec change ("CURA fixed past-date validation in deployment X", "the appointment form's date input was renamed").
- The user is amending the FRD by hand and wants the tests pulled along.
- A `review-suite-stability` audit surfaced a _surprise green_ on a gap test that, on investigation, is real (not §A-ENV-1 contention) — that's the
  entry point for resolving the gap.
- An `IDENTIFIED_GAPS.md` entry needs to be marked resolved.

## What this skill does NOT do

- It does not invent FRD content. The one-sentence statement of the change comes from the user.
- It does not write new tests for fresh requirements. Use `extend-coverage` to find adjacent gaps, then `empiricism` to author them.
- It does not run the full suite preemptively — affected scenarios only, on both browsers, after the user signs off on the plan.
- It does not commit or push. That's the `pr-report` skill + the user's call.
