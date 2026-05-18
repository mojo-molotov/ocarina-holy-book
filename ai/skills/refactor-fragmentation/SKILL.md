---
name: refactor-fragmentation
description:
  "**Refactoring skill for extracting repeated test-chain pieces into Ocarina `TestScenarioFragment`s** — the `pre_test_scenarios_fragments` /
  `post_test_scenarios_fragments` / inline-fragment composition surface that lets the same sub-chain (login, navigate-to-form, accept-banner) be
  reused across scenarios. The skill identifies repeated chain patterns and proposes fragmentations — but **only after two gates pass**: (1) the
  codebase is large enough that fragmentation pays for itself (a four-test suite gains nothing by extracting a two-step login fragment), and (2) the
  **user has stated their DRY policy** explicitly. The policy ranges from 'no DRY, repetition is fine' through 'strict DRY everywhere' to 'a balanced
  middle the user refines over time'. The skill never decides the policy unilaterally; it asks. Once the policy is set, the audit applies it to the
  repeated patterns it found, surfaces the candidates ranked by repetition count + cost-of-non-DRY, and stops — the user picks which to fragment. Use
  whenever the user asks to extract fragments, audit chain repetition, plan a fragmentation refactor, or set up the pre/post-test fragment surface for
  the first time."
---

# Refactor through fragmentation — only after the gates pass

A refactoring skill for Ocarina's `TestScenarioFragment` primitive (see `<gitignored>/ocarina/.../custom_types/oc_test.py`:
`type TestScenarioFragment[Driver] = Callable[[Driver, ILogger], TestChain]` and the `pre_test_scenarios_fragments` / `post_test_scenarios_fragments`
slots on tests). Fragments let a sub-chain (login, navigate-to-form, accept-banner, logout) be defined once and composed into many scenarios.

Fragmentation is _good when it earns its keep_ and _bad when it doesn't_. A four-test suite doesn't benefit from extracting a two-step login; a
forty-test suite where every test needs the same six-step setup absolutely does. The middle is judgment, and the judgment is the user's, not the
skill's.

So the skill has **two non-negotiable gates** before it surfaces any fragmentation proposals.

## The two gates

### Gate 1 — Is the codebase large enough?

Heuristics, soft thresholds:

- **Under ~6 test files** in `src/tests/scenarios/`: the audit _runs but warns_ — fragmentation is likely premature.
- **6–15 test files**: fragmentation may pay off if repetition is high; surface candidates with confidence ranking.
- **15+ test files**: fragmentation is usually a win; surface aggressively.

These are not hard cutoffs. A 4-test suite with 100% identical 8-step setups might still benefit; a 30-test suite with all-unique flows won't.

For the current project, count `src/tests/scenarios/**/*.py` (excluding `__init__.py`, `datasets/`). If the count is under the soft threshold, the
audit's verdict line names that explicitly: _"Codebase has N test files; fragmentation likely premature — proceed only if a specific 6+-step pattern
repeats verbatim across 3+ tests."_

### Gate 2 — What's the user's DRY policy?

The skill **asks** before proposing. The policy frames every recommendation. Common positions:

- **No DRY** — _"Repetition is acceptable; readability of the in-place chain wins over reuse."_ In this mode, the skill surfaces repetition but
  proposes no fragments; the deliverable is "here's what's repeated, you don't want to extract, OK".
- **Strict DRY** — _"Every repeated chain piece should become a fragment, even short ones."_ The skill aggressively proposes; surface all repeats of ≥
  2 steps.
- **Balanced** — _"Extract when it clearly pays off; don't extract for two-step setups."_ Default position for most codebases. The skill applies a
  threshold (e.g. fragment when ≥ 4 steps and ≥ 3 occurrences) and ranks candidates.
- **Balanced, refining over time** — _"I'll refine the policy as the codebase grows."_ Same as Balanced for the immediate pass, plus a note in the
  surface that thresholds should be revisited after the next coverage push.

Ask early. If the user has already stated a policy in conversation or in `CLAUDE.md`, cite the prior statement; don't re-ask. If no policy exists, the
skill **must ask before producing the catalogue**. Surface the question with the four positions above.

## What counts as a fragmentation candidate

A repeated sub-sequence of test-chain steps appearing in ≥ N scenarios where:

- Same connector / POM operations.
- Same order.
- Equivalent inputs (constants, not just compatible values) — diverging inputs make the "same" looser.
- Pre-test (setup-shaped) or post-test (teardown-shaped) or inline-in-flow.

The Ocarina primitive supports:

- **Pre-test fragments** — `pre_test_scenarios_fragments` runs before the scenario's main chain.
- **Post-test fragments** — `post_test_scenarios_fragments` runs after.
- **Inline composition** — a fragment factory called from within a scenario, its returned chain spliced in.

The skill identifies which surface fits each candidate.

## Cross-cutting concerns to surface alongside candidates

- **Setup / login** — almost always the prime fragment candidate; "log in as DEMO_USERNAME and land on home" is a canonical pre-test fragment.
- **Teardown / logout** — same on the post-test side.
- **Navigate-to-page** — "go to history" or "open the appointment form" if it appears in ≥ 3 scenarios.
- **Component dismissal** — if a `match_page` branch or watcher-adjacent dismissal repeats (cookie banner, "are you sure?" modal), the dismissal steps
  may fragment.
- **Smoke vs main parity** — smoke scenarios often duplicate a slice of a main scenario; smoke is fine to leave alone (smoke wants standalone
  readability), but the duplication is worth surfacing.

## Procedure

### Step 1 — Count the test files (Gate 1)

```bash
find src/tests/scenarios -name "*.py" \! -name "__init__.py" \! -path "*/datasets/*" | wc -l
```

If under the soft threshold (~6): surface the warning at the top of the audit. Don't bail entirely — proceed but make the verdict line acknowledge the
premature-fragmentation risk.

### Step 2 — Ask the user's DRY policy (Gate 2)

Unless already established in `CLAUDE.md` or the recent conversation. Present the four positions; capture the answer. The whole audit is shaped by
this choice.

### Step 3 — Map the chain shapes

For each scenario, read the chain (the `test_chain` / connector sequence). Capture the sequence as a normalised list of (connector / operation,
kwargs-shape). Don't capture full kwarg values — the shape is what matters for matching.

```bash
grep -rn "from.*connectors.*import\|drive_page\|match_page" src/tests/scenarios --include="*.py"
```

For component-level operations (logout via Sidebar, login via LoginPage), capture the operation name; the underlying selectors are POM-internal.

### Step 4 — Find repeated sub-sequences

For each pair (or N-tuple) of scenarios, find the longest common sub-sequence(s). For each:

- Length (steps).
- Occurrences (in how many scenarios).
- Position (pre / post / inline).
- Input divergence (do all occurrences use the same constants, or do values vary?).

Apply the policy threshold:

- **No DRY policy** → surface all, propose nothing.
- **Strict DRY** → propose all with ≥ 2 steps and ≥ 2 occurrences.
- **Balanced** → propose all with ≥ 4 steps and ≥ 3 occurrences (defaults; user can override the numbers).
- **Balanced, refining** → same as Balanced for now, mark the thresholds as revisitable.

### Step 5 — Classify each candidate

- **Pre-test fragment candidate** — repeats before the main chain.
- **Post-test fragment candidate** — repeats after.
- **Inline fragment candidate** — repeats mid-chain.
- **Cross-position candidate** — same sub-sequence appears in pre / post / inline depending on scenario; harder to fragment cleanly.

For each, identify the connectors / POMs involved and the file that should _own_ the fragment (commonly `src/lib/fragments/` or `src/tests/fragments/`
— surface the choice; don't unilaterally create a new directory).

### Step 6 — Surface the catalogue

```markdown
# Fragmentation audit — <project-name> (<date>)

## Gates

- **Codebase size**: N test files. <Within range | Likely premature, proceed with caution>.
- **DRY policy**: <No DRY | Strict | Balanced | Balanced refining-over-time> — <if provided in this session: quoted | if from CLAUDE.md: cited>.

## Candidates (ranked by repetition × length × cost-of-non-DRY)

### Pre-test fragment candidates

- **`login_as_demo_user`** — login + land-on-home, 4 steps, repeated in <K> scenarios:
  - `<scenario file>:<line>`
  - `<scenario file>:<line>`
  - ... Cost-of-non-DRY: <high — change to login flow requires touching K files | medium | low>. Recommended owner: `src/lib/fragments/login.py`
    (suggested; surface choice for confirmation). Input divergence: <none — all use `DEMO_USERNAME` / `DEMO_PASSWORD` | minor — alternate flows pass
    different waits>.

- ...

### Post-test fragment candidates

- ...

### Inline fragment candidates

- ...

### Cross-position candidates

- (Harder to fragment cleanly. Surface for awareness; the user may prefer to leave these inline.)

## Surfaced repetitions below the policy threshold (informational)

- <repeat shape>: <K occurrences>, below the threshold but worth noting if the codebase grows.

## Out-of-scope candidates

- Smoke scenarios duplicating slices of main scenarios — usually intentional (smoke wants standalone readability). Surface but recommend leaving.

## Cross-references

- Ocarina `TestScenarioFragment` (`<gitignored>/ocarina/.../custom_types/oc_test.py:72`).
- `CLAUDE.md` — DRY policy section (if it exists).
- Related skills: `review-compartmentalisation-leaks` (literals migrated to constants), `extend-coverage` (new tests may exercise the fragment),
  `review-dead-code` (run after fragmentation lands — the original blocks the fragment replaced often turn into orphan helpers).

## Recommended next motions

- For each accepted candidate: a fragmentation PR per candidate (or one PR per group of related candidates). The skill describes the move; the user
  authors it.
- For the policy itself: if the user picked "Balanced refining-over-time", schedule a revisit after the next coverage push.

## Verdict

<one-line: N candidates above the policy threshold, K below, codebase size <within | premature>, policy <stated | needs revisit>>.
```

Print the catalogue.

### Step 7 — Stop. The user decides.

Each candidate resolves as:

- **Fragment** — the user (or a follow-up edit motion) extracts the sub-chain into a `TestScenarioFragment`, wires it into the scenarios via the
  appropriate slot.
- **Leave inline** — the user judges the readability cost beats the DRY benefit for this candidate.
- **Defer** — record for the next refactor pass.
- **Revisit policy** — the user changes their DRY stance; re-run the audit with the new policy.

## Hard rules

- **Gate 1 first.** Small codebases get the warning before any catalogue is produced. Premature fragmentation creates indirection without benefit.
- **Gate 2 always.** The DRY policy comes from the user, never from the skill. If unknown, _ask_ — do not produce a catalogue without it.
- **Don't propose creating new directories unilaterally.** A `src/lib/fragments/` directory is a project-shape decision. Surface as a suggestion; the
  user confirms.
- **Don't fragment when input divergence makes the "same" loose.** Two flows that _call the same connectors_ but with different inputs are not the
  same chain — extracting them into a single fragment risks coupling unrelated motions.
- **Smoke duplication is usually OK.** Smoke wants to be standalone; readability beats DRY for the gate that decides whether to run anything else.
- **A fragment is authoring data.** Per "Datasets are authoring decisions" — every proposed fragment is a candidate the user must sign off on, not a
  fix to apply.
- **Static review only.** The skill surfaces; the user applies.
- **Once the policy is set, stick to it across the audit.** Don't apply Strict criteria to half the candidates and Balanced to the other half.
- **Re-run after coverage growth.** A "premature" verdict today becomes "ready" after 10 more scenarios. The audit's recommendations expire fast.

## When to run this skill

- After a coverage push that added several scenarios — the surface area for repetition just grew.
- When a contributor notices the same setup steps in many tests and asks whether to extract.
- Before a release if the team wants the codebase tidy.
- When introducing a new fragment surface (first use of `pre_test_scenarios_fragments`) — establish the convention.
- After a `review-compartmentalisation-leaks` pass moved literals to constants — fragments are the next layer of DRY.

## What this skill does NOT do

- It does not extract fragments. Surfaces; user applies.
- It does not pick the DRY policy. Asks the user.
- It does not create directories or modules unilaterally. Suggests; user confirms.
- It does not propose fragmentation when input divergence is high — extracting heterogeneous flows into one fragment hurts more than it helps.
- It does not run the suite after recommending. Verifying the refactor didn't break anything is the user's motion.
- It does not modify Ocarina internals. Uses the public `TestScenarioFragment` surface.
- It does not include attack-shape literals in any fragment. Per `CLAUDE.md` → "Security testing is functional and static — never active".
