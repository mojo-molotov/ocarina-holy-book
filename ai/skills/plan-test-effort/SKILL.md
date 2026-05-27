---
name: plan-test-effort
description:
  Produce a **lightweight, first-pass test-effort plan** — the naïve baseline before any deeper estimation method (risk-based testing, ISO 25010
  quality-model weighting, historical-defect analysis, capacity modelling) is brought in. Enumerates the FRD's requirements with a coarse criticality
  grade (critical / major / minor) anchored in **business impact on the SUT as it actually exists** (not on category priors about what an app of this
  kind "should" do); evaluates risk with a two-axis shape (likelihood × impact, three buckets each) per requirement or feature cluster; folds those
  into a relative effort weight (S / M / L) per area; surfaces the open questions that would justify a deeper pass. The deliverable is a single
  document (`TEST_EFFORT.md` by default) — explicitly labelled as a *first cut*, not the final word. Use when the user asks to scope test effort on a
  new project, sketch a budget, prioritise where to invest tests first, draft a baseline that a later risk-based / quality-model / capacity pass will
  refine, or onboard a team to the shape of the test investment. Surface as a proposal; never auto-commit; pairs upstream with `assess-ecosystem`
  (what the SUT *is*) and `write-test-strategy` (what the suite *exercises*); pairs downstream with deeper effort skills as they're added.
---

# Plan the test effort — first-pass, naïve baseline

A test-effort plan is the legible map of _where the testing investment goes_ — which requirements warrant the most attention, which risks dominate the
picture, which features get the budget. This skill produces the **first cut**: the basics, the foundational questions, the shape a team needs before
any deeper method (risk-based testing per ISO 31000, FMEA, quality-model weighting per ISO 25010, historical-defect-rate modelling, capacity planning)
is worth applying.

Why a naïve baseline first: deeper methods need real inputs — defect history, stakeholder workshops, capacity numbers, a calibrated risk taxonomy.
None of those exist on day one. A first-cut effort plan, honestly labelled as such, lets the team start somewhere and gives the deeper passes a target
to refine.

**Surface, don't apply.** The skill produces the doc as a proposal; the user reviews and signs off before commit.

**Generated from the SUT and the FRD, not invented.** Every criticality grade, every risk row, every effort weight names a requirement or feature that
actually exists in the FRD or in the deployed SUT. No category priors about "what an app of this kind should have" — if the SUT doesn't have the
surface, it doesn't appear in this plan. (Same discipline as `write-test-strategy` §1 Scope: invented surfaces are noise.)

Default target: `TEST_EFFORT.md` at the repo root. For a different location, ask.

## What the doc contains

Five sections. Numbering matters — readers cite by section.

| §   | Section                            | Where the content comes from                                                                                       |
| --- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 1   | Frame                              | One paragraph: what this plan is and isn't; explicit "first-cut, naïve" framing; list of inputs not yet available  |
| 2   | Requirements & criticality         | Every FRD requirement, graded **critical / major / minor** with a one-line business-impact rationale               |
| 3   | Risk register (lightweight)        | One row per area; **likelihood × impact** on a three-bucket scale (low / medium / high); the _concern_ in one line |
| 4   | First-cut effort allocation        | Per feature / area: relative weight **S / M / L** derived from §2 + §3; explicit "why this weight"                 |
| 5   | Open questions for the deeper pass | What inputs are missing; what method would justify a refinement (FMEA, ISO 25010, capacity, defect history)        |

Five, deliberately. A first-cut plan that needs more than five sections is no longer first-cut. The discipline is to leave the eighth-decimal-place
questions for the deeper passes that this skill stops short of.

## The criticality scale (§2)

Three grades. Anchor each in **business impact on the SUT as it exists today**, never on a category prior.

| Grade        | Discriminating question                                                                                                                |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Critical** | Failure makes the SUT unusable for its primary purpose, or causes irrecoverable user data loss, or breaks a hard regulatory boundary.  |
| **Major**    | Failure significantly degrades a primary user journey but the SUT remains usable (workaround exists, or a secondary path still works). |
| **Minor**    | Failure causes inconvenience or cosmetic divergence; primary journeys unaffected.                                                      |

The hard part is honesty: most requirements are not critical. A flat "everything is critical" grading is a sign the rater is hedging, not analysing.
If §2 has more than ~30% critical rows, the discriminator has slipped — re-read the question and re-grade. The whole point of the scale is to make the
top of the list short.

**Category-prior trap.** Don't grade by what "an app of this kind ought to protect": grade by what _this_ SUT actually does. A healthcare-shaped demo
with no payment surface has no payment-related rows in §2 at all — not even as "critical, untested" — because the surface doesn't exist. Same filter
as `write-test-strategy`: absence from the SUT means absence from this doc.

## The risk register (§3)

Lightweight, on purpose. Three buckets per axis. The full FMEA / risk-priority-number / Monte-Carlo workup is the deeper pass.

| Axis           | Low                              | Medium                                                                 | High                                                                                                |
| -------------- | -------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Likelihood** | Defect type is rarely seen here. | Defect type is plausible given the SUT's shape and the team's history. | Defect type has already occurred or is structurally invited (e.g. shared singleton, no validation). |
| **Impact**     | Inconvenience; easily noticed.   | One user journey degraded; recoverable.                                | Multiple journeys broken, data lost, or a critical FRD requirement violated.                        |

Render each row as: `area · likelihood · impact · concern · current coverage`. The `current coverage` column anchors the risk against what the suite
actually exercises today (cross-reference the existing `tests/scenarios/**` if the suite already exists; "none yet" is a legitimate value on a new
project).

The product of likelihood × impact is not a hard ranking yet — that's the deeper pass. At this level, _surface_ the medium-high and high-high cells as
the first candidates for the budget in §4.

## The effort weight (§4)

Three weights: **S** (small — one or two scenarios), **M** (medium — a feature campaign, several scenarios + at least one gap test), **L** (large — a
campaign that needs its own POM family, dispatcher discipline, or a coordination layer per `understand-sut-constraints`).

Derive each row's weight from §2 + §3:

- **Critical + high risk** → L by default; justify if you go lower.
- **Major + medium risk** → M by default.
- **Minor + low risk** → S by default.
- **Mismatch (e.g. critical + low risk)** → use the higher of the two; explain the mismatch in one line.

The "explicit why" is non-negotiable. An effort weight without a one-line rationale is the kind of number that drifts the first time the team's mental
model shifts. The rationale ties the number back to §2/§3 so a future reader can re-derive (or re-grade) it.

## Procedure

### Step 0 — Pre-flight

Confirm the inputs:

- The FRD (or whichever artifact the project uses — `CLAUDE.md` enumerates the names). If absent, **stop** and walk `assess-ecosystem` first; without
  a spec, this skill has nothing to grade.
- The deployed SUT, browsable. If only source is available, note it as a limitation; criticality grading needs to see the actual user experience.
- Any existing gap inventory. Pre-existing gaps inform §3 (defect history is the lowest-effort risk signal available on day one).
- The current `tests/scenarios/**` tree, if any. Used as the `current coverage` column in §3.

### Step 1 — §2 (requirements & criticality)

Enumerate every requirement from the FRD. For each:

- Quote the requirement ID and one-line statement.
- Grade **critical / major / minor** against the discriminating question.
- Add a one-line rationale tied to **what breaks for the user** if the requirement isn't met, in this SUT.

Re-check the distribution: if >30% critical, re-read the discriminator and re-grade. Most requirements are major or minor; that's the expected shape.

### Step 2 — §3 (risk register)

For each feature / area (not per requirement — risk clusters above the requirement level), surface:

- The concern in one line — what could go wrong, in plain language.
- Likelihood (low / medium / high) using the table above.
- Impact (low / medium / high).
- Current coverage — name the scenarios that exercise it, or "none yet".

Sources for the concern:

- The gap inventory (defects already seen).
- The structural shape of the SUT (a shared demo account → contention; widget-decorated inputs → interception; back-button + auth → BFcache).
- `understand-sut-constraints` if the SUT looks load-shaped.
- `assess-ecosystem` if third-party dependencies are in the picture.

### Step 3 — §4 (first-cut effort allocation)

Per feature / area:

- Apply the default mapping (Critical+High → L, Major+Medium → M, Minor+Low → S).
- Note mismatches and override deliberately.
- One-line rationale citing the §2 / §3 row(s) that drove the weight.

Sanity-check the total shape: a plan where everything is L is dishonest about the budget; one where everything is S underestimates the SUT. Expect a
mix.

### Step 4 — §5 (open questions for the deeper pass)

What would push this plan from naïve to calibrated? Typical entries:

- _"No historical defect data available. After one release cycle, re-grade §3 likelihood against the actual defect distribution."_
- _"No capacity numbers. A capacity-modelling pass would set absolute weights in §4, not relative ones."_
- _"FRD lacks acceptance criteria for §X.Y. An `update-frd-and-tests` motion would specify, then §2 could grade more confidently."_
- _"Risk-based testing per ISO 31000 would consolidate §3 into a single risk-priority number; not worth doing until §2 stabilises."_
- _"ISO 25010 quality-model weighting (functional suitability vs reliability vs usability vs ...) would re-balance §4. Defer until the suite has
  coverage across the model's sub-characteristics."_

These are pointers, not commitments — list what _would_ refine the plan and what it would cost.

### Step 5 — §1 (frame)

Write the framing paragraph last, once §2–§5 are stable. Spell out:

- This is a first cut. It will be wrong in detail. It is right in shape.
- The inputs the deeper pass would need (gathered from §5).
- The skill it was produced by; the date.

### Step 6 — Surface the plan

```markdown
# Test-effort plan — `<SUT>` (first cut, <date>)

## §1 Frame

<one paragraph: naïve baseline; what's missing; what would refine it>

## §2 Requirements & criticality

| Req ID       | Statement              | Grade    | Business-impact rationale  |
| ------------ | ---------------------- | -------- | -------------------------- |
| `<FRD §X.Y>` | <one-line requirement> | Critical | <what breaks for the user> |
| `<FRD §X.Y>` | <one-line requirement> | Major    | <what breaks for the user> |
| `<FRD §X.Y>` | <one-line requirement> | Minor    | <what breaks for the user> |

## §3 Risk register (lightweight)

| Area        | Concern            | Likelihood | Impact | Current coverage         |
| ----------- | ------------------ | ---------- | ------ | ------------------------ |
| `<feature>` | <one-line concern> | High       | High   | `<scenarios>` / none yet |

## §4 First-cut effort allocation

| Area        | Weight | Why                                                       |
| ----------- | ------ | --------------------------------------------------------- |
| `<feature>` | L      | Critical (§2 row Z) + high risk (§3 row Y) → L by default |
| `<feature>` | M      | Major (§2 row …) + medium risk (§3 row …) → M by default  |
| `<feature>` | S      | Minor (§2 row …) + low risk (§3 row …) → S by default     |

## §5 Open questions for the deeper pass

- <missing input + the method that would consume it>
- <missing input + the method that would consume it>

## Verdict

<one-line: N critical reqs, K high-high risks, total weight skew (e.g. "L-heavy, expected for a greenfield"), top three areas to staff first>
```

Print the report. Stop. The user decides what lands.

## Re-running this skill

Re-run when:

- The FRD changes (new requirements, removed requirements, reworded acceptance criteria).
- A release cycle completes and defect data is now available — §3 likelihood can be re-graded against reality (and the verdict probably shifts).
- The deeper pass (ISO 25010 weighting, FMEA, capacity modelling) is being prepared and wants the latest naïve baseline as input.
- A new feature lands in the SUT.
- A new gap is filed in the gap inventory that changes a §3 row from low to medium or higher.

Don't re-run as routine maintenance; the plan is a snapshot. The deeper pass replaces it; the naïve baseline does not need monthly polish.

## Hard rules

- **First-cut, labelled as such.** Every surfaced plan opens with the "naïve baseline" framing in §1. The skill never produces a document that looks
  like a final calibration.
- **No category priors.** Same discipline as `write-test-strategy` §1: only enumerate surfaces, requirements, and risks that exist in the FRD or the
  SUT. Don't list "payment" because "an app of this kind usually has payment"; don't grade a non-existent feature; don't risk-rate an absent surface.
  If the SUT doesn't have it, it's not on the plan.
- **Three buckets, not five.** Both §2 (critical / major / minor) and §3 (low / medium / high) use three buckets each. Five-bucket scales feel precise
  and aren't — they invite hedging at the middle. Three forces a choice.
- **Distribution check.** If §2 has more than ~30% critical or §3 has more than ~20% high-high, re-read the discriminator. The whole point of the
  grading is to make the top of the list short.
- **One-line rationale on every row.** §2 needs a business-impact line; §3 needs a concern line; §4 needs a "why this weight" line. A row with no
  rationale is one a future reader can't audit — and so a row that quietly drifts.
- **Generated from the spec and the SUT.** Open the FRD, open the deployed app, read the gap inventory. Don't grade from memory; quote IDs and link to
  the source artifacts.
- **Surface, don't apply.** This skill writes a proposal; the user signs off before commit. Never auto-write `TEST_EFFORT.md`.
- **Per `CLAUDE.md`: security testing is functional and static — never active.** Risk rows about security stay on the comprehension side; no proposed
  active probes.

## Cross-references

- **Upstream** (run before): `assess-ecosystem` (when the FRD is thin or the third-party shape is unclear), `understand-ocarina` (when the team is new
  to the framework's shape), `understand-sut-constraints` (when the SUT's parallel-safety envelope is part of the risk picture).
- **Sibling**: `write-test-strategy` — this skill plans the _investment_; `write-test-strategy` documents the _suite that resulted_. The two coexist;
  one is forward-looking, the other is the rear-view mirror.
- **Downstream** (consumes this plan): `extend-coverage` (for high-weight areas with thin coverage), `update-frd-and-tests` (for §5 open questions
  that resolve via spec clarification), `manage-backlog` (each S/M/L area can be sliced into backlog rows).
- **Deeper-pass successors**: future skills covering ISO 31000 risk-based testing, ISO 25010 quality-model weighting, FMEA-style failure-mode
  enumeration, historical-defect-rate calibration, capacity modelling. Each consumes this naïve baseline as input.

## When to run this skill

- First authoring on a new project — before `write-test-strategy`, ideally.
- Onboarding a new team or a new tester — the plan is faster to read than the strategy doc and frames the investment.
- Before a release planning meeting — even a naïve plan moves the conversation from "test everything" to "here's where the budget should go".
- After a significant SUT change (new feature, dropped feature, regulatory shift) — re-grade §2.
- As a precursor to commissioning a deeper pass — surface §5 so the deeper method has a clear question to answer.

## What this skill does NOT do

- It is not a calibrated risk assessment. ISO 31000 / FMEA / risk-priority-number scoring is the deeper pass; this skill is the rough sketch that asks
  whether the deeper pass is worth doing yet.
- It does not produce a calendar / Gantt / staffing plan. Effort weights (S / M / L) are relative, not absolute hours.
- It does not weight by quality-model sub-characteristic (ISO 25010 — functional suitability vs reliability vs usability vs portability vs ...). That
  refinement belongs to a successor skill.
- It does not consume defect history. A historical-defect-rate calibration is a successor skill; this one notes the absence in §5.
- It does not author tests, suites, or scenarios. `extend-coverage` and `write-test-strategy` are downstream.
- It does not modify the FRD. Spec gaps surface in §5 as open questions; `update-frd-and-tests` is the motion that resolves them.
- It does not commit. The deliverable is a proposal; the user decides what lands.
