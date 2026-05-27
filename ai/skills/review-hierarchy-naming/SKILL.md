---
name: review-hierarchy-naming
description:
  Audit the **naming of nodes in the `TestCycle → TestCampaign → TestSuite → Test` hierarchy** for the lazy-naming antipattern where a child carries
  the same (or near-same) name as its parent — most commonly a `TestCampaign` containing a `TestSuite` of the same name. A suite is meant to be a
  *segment* of the campaign it belongs to; a same-name child collapses the hierarchy in the reader's head ("Authentication › Authentication") and
  tells you nothing about what makes that segment distinct from the campaign. Almost always a symptom of authoring under time pressure with a single
  feature suite in the campaign and no second axis to name it on. Use whenever the user asks to audit hierarchy naming, find lazy / redundant names in
  the cycle, review the strategy doc's tree for clarity, or harden the suite tree before a release-readiness pass. Surface candidates with one-line
  rationales and naming hints; never rename a node. Renames touch the strategy doc, scenario imports, and PR-description hierarchy slices — they
  belong with the user.
---

# Review — hierarchy naming (parent ⊃ same-name child)

The principle. Ocarina's hierarchy is `TestCycle → TestCampaign → TestSuite → Test`. Each level adds a discriminator the level above can't carry on
its own:

- A **campaign** groups _what feature / concern_ is exercised.
- A **suite** carves a campaign into _segments_ — happy paths vs failure modes vs baseline; per-browser; per-environment; per-shape of input.

When a suite carries the same name as its parent campaign — `Campaign("Authentication") ⊃ Suite("Authentication")` — the hierarchy collapses in the
reader's head. The level is there in the tree but tells you nothing the parent didn't already say. It's almost always a symptom of one of the two
shapes:

1. **Lazy single-segment campaign.** The campaign contains exactly one suite, and at authoring time the author had no second axis to name it on, so
   they reused the campaign's name. The fix is to **rename the suite for its actual scope** ("Happy paths", "Baseline", "Smoke prerequisites"). The
   hierarchy is strict in Ocarina (`Test → TestSuite → TestCampaign → TestCycle`) — you cannot collapse a level by moving tests directly into a
   campaign. If after the rename the discriminator still feels thin, that's a hint to revisit the suite's _composition_ (split it along a real axis,
   or reconsider whether this campaign should merge with an adjacent one), not to alter the levels.
2. **Mirror naming by reflex.** Multiple suites under the campaign and one of them inherits the campaign's bare name as a "default" / "main" /
   "catch-all" segment. The fix is to **name it for what it actually catches** (the discriminator the other siblings _don't_ have).

The audit finds those. **It never renames.** A rename touches the strategy doc's coverage tree (§6), the cycle file's imports, the suite factory's
`name=` literal, and any PR-description hierarchy slices that quote the old name — the user owns the propagation.

Default target: `src/tests/cycles/<cycle>.py` + `src/tests/campaigns/**/*.py` + `src/tests/suites/**/*.py` against the test-strategy doc §6. For a
different repo layout, ask the user.

## What counts as a collision

Three flavours, in order of how often they appear in practice:

| Flavour             | Shape                                                                                     | Example                                                          |
| ------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Exact match**     | Child's `name=` string is byte-equal to the parent's `name=`.                             | `Campaign(name="Authentication") ⊃ Suite(name="Authentication")` |
| **Near-match**      | Differs only by case, whitespace, plural, or a trivial suffix ("tests", "suite", "main"). | `Campaign(name="History") ⊃ Suite(name="History tests")`         |
| **Semantic mirror** | Different words, identical meaning — synonyms a reader wouldn't parse as a discriminator. | `Campaign(name="Authentication") ⊃ Suite(name="Login & logout")` |

Exact and near-match are mechanical — grep finds them. Semantic mirror needs a read of the strategy doc + a moment of judgement; surface as a softer
"consider" candidate rather than a hard finding.

The same shape applies one level down: a `TestSuite` containing a `Test` with the same name is the same antipattern. (Less common, because Ocarina
test names tend to be sentence-shaped; still worth surfacing if it appears.)

## What does NOT count

Some same-name shapes are not collisions — call them out so the audit doesn't surface noise:

- **A single-suite campaign deliberately mirroring on purpose** because the campaign is a thin wrapper for a hard structural reason (e.g. it has to
  exist for the cycle's smoke-gate machinery to attach to it). Surface as a candidate, but the user may legitimately keep it.
- **A name that's the FRD's own term for the feature** and the suite genuinely covers _all_ of it (no other suites in the campaign, no second axis
  available). That's the "one-segment" case — surface it as low-confidence; a rename to a generic segment label ("Happy paths", "Baseline") is usually
  still an improvement on the mirror, but the user may judge that the mirror is honest about the structure and keep it.
- **The cycle itself sharing a name with its top campaign** in projects with only one campaign. That's a different antipattern (the cycle is
  underused) but it's not _this_ one.

## Procedure

### 1. Build the hierarchy map

Walk imports from the cycle file inward. The cycle calls factories, not constructors (`CLAUDE.md` → _"The cycle file calls factories, not
constructors"_), so a literal-text grep for `TestCampaign(` and `TestSuite(` only finds the constructors inside the factory files.

```bash
# Find the cycle file
ls src/tests/cycles/

# Extract every campaign factory the cycle wires
grep -nE "create_\w+_campaign\(" src/tests/cycles/*.py

# For each campaign factory, extract its name= literal and the suite factories it calls
grep -nE 'TestCampaign\(|name=' src/tests/campaigns/**/*.py

# For each suite factory, extract its name= literal
grep -nE 'TestSuite\(|name=' src/tests/suites/**/*.py
```

Render the map (in-memory; this is audit scratch, not a deliverable):

```
Cycle: <cycle name>
  Campaign: <campaign name>
    Suite: <suite name>
    Suite: <suite name>
  Campaign: <campaign name>
    Suite: <suite name>
```

### 2. Pair each child with its parent and check

For every `(parent, child)` pair in the map:

- **Exact match** — flag.
- **Near-match** (case-fold + strip whitespace + strip "tests"/"suite"/"main" + singularise) — flag.
- **Semantic mirror** (synonym or rewording with no discriminator) — flag as a soft candidate, lower confidence.

Cross-reference §6 of the strategy doc. If the strategy doc's tree shows the same flat-named child, the antipattern is already visible to readers; the
rename is overdue. If the strategy doc has _already_ paraphrased the child to a more specific name than the code's `name=` literal, the code is the
laggard — surface as a "code/doc drift" finding.

### 3. For each flagged pair, propose a rename

Only one remedy applies within Ocarina's strict hierarchy: **rename**. The framework does not allow collapsing a level (no skipping `TestSuite` to
attach tests directly to a `TestCampaign`, no skipping `TestCampaign` to attach a suite directly to a `TestCycle`), so the four levels stay; what
shifts is the label on the colliding one.

What would the suite be _called_ if it had to differ from the parent? Look at the suite's tests:

- If the tests are all happy paths → "Happy paths".
- If they're all failure modes → "Failure modes".
- If they're the baseline scenarios that gate the rest → "Baseline" / "Smoke prerequisites".
- If they're data-driven over an input space → name the input axis ("Login credentials matrix", "Date-boundary matrix").
- If the tests really don't share a discriminator → that's a hint to revisit the suite's _composition_ (split it along a real axis, or reconsider
  whether the campaign should merge with an adjacent one that has more axes). Surface that as a follow-up; don't try to invent a label that hides the
  composition smell.

### 4. Surface the report

```markdown
# Hierarchy-naming audit — `<cycle>` (<date>)

## Map
```

<rendered cycle → campaign → suite tree, with same-name pairs highlighted>

```

## Findings

### Exact / near-match

| Parent (Campaign)     | Child (Suite)         | Flavour    | Other siblings under parent              | Suggested rename                              |
| --------------------- | --------------------- | ---------- | ---------------------------------------- | --------------------------------------------- |
| `Authentication`      | `Authentication`      | exact      | (none — single-segment)                  | `Happy paths` / `Baseline`                    |
| `History`             | `History tests`       | near-match | `History — failure modes`                | `Happy paths` (matches the sibling pair)      |

### Semantic mirror (lower confidence — needs judgement)

| Parent (Campaign)     | Child (Suite)         | Why mirrored                              | Suggested rename or note                |
| --------------------- | --------------------- | ----------------------------------------- | --------------------------------------- |
| `Authentication`      | `Login & logout`      | Synonym pair; no second axis vs siblings  | Consider `Happy paths` if that's the actual segment scope. |

### Code/doc drift

- `<campaign>/<suite>` — code says `name="<old>"`, strategy doc §6 paraphrases as `<new>`. The strategy doc is closer to right; the code is the laggard.

## Verdict

<one-line: N exact/near-match, K semantic mirrors, J drift; whether the cycle's tree is overall legible or whether more than one rename is overdue>.
```

Print the report. **Do not rename.**

### 5. Stop

The audit is the deliverable. Renames are the user's decision per finding because:

- The `name=` literal flows into run reports, DOCX titles, and PR-description hierarchy slices.
- A rename touches the strategy doc §6 simultaneously to stay consistent.
- One rename may invite a re-shape of the campaign (split the suite along a real axis, merge the campaign with an adjacent one) — that's a design
  call, outside this skill's scope.

Pair with `update-frd-and-tests` if the rename is part of a broader spec/structure change; with `pr-report` for the eventual hierarchy slice in the PR
description.

## Hard rules

- **Surface, don't rename.** No code edits. The user owns the propagation.
- **Read the strategy doc §6 every run.** It's the authoritative view of the cycle tree from the reader's perspective; the audit's job is to compare
  the code's `name=` literals to that view.
- **Don't propose names from category priors.** "Happy paths" / "Failure modes" / "Baseline" are suggestions because they map to the test-type
  taxonomy (`write-test-strategy` §3). If the suite's tests don't actually cluster into one of those, surface the mismatch rather than invent a
  plausible-sounding label.
- **Semantic-mirror findings are softer.** Surface them as "consider" — they need a read of the tests, not just the names, and false positives are
  more likely.
- **One pass at a time.** Don't bundle this audit with renames or with a strategy-doc rewrite. Surface, hand off, stop.

## Cross-references

- **Sibling reviews**: `review-comment-drift` (comments diverging from code), `review-suite-stability` (per-test category audit against the strategy
  doc), `review-intent-collisions` (collisions between gap tests and happy-path tests).
- **Authoring**: `write-test-strategy` (renders the §6 tree this audit reads against), `update-frd-and-tests` (the change-propagation skill if a
  rename rides with a broader update).
- **Refactor follow-up**: a rename is mechanically a code change but conceptually an authoring decision — the user applies, then `pr-report` shapes
  the hierarchy slice in the PR description.

## When to run this skill

- Before a release-readiness pass — the strategy doc's tree is the reader's first impression; lazy names dull it.
- After adding a new suite to an existing campaign — the new sibling sometimes inherits the bare campaign name out of authoring inertia.
- When `write-test-strategy` surfaces a §6 row that reads weirdly ("Authentication › Authentication › `valid_login`") — that's the audit's trigger
  from the doc side.
- Onboarding — a fresh reader sees the redundancy faster than the author.

## What this skill does NOT do

- It does not rename. It surfaces candidates and proposes a rename.
- It does not propose collapsing levels. Ocarina's hierarchy is strict (`Test → TestSuite → TestCampaign → TestCycle`); the four levels are
  non-negotiable, and the only remedy this skill ever suggests is a label change. Splitting a suite along a real axis, or merging a campaign with an
  adjacent one, are design decisions the user owns — surface as a follow-up, never as the audit's recommendation.
- It does not audit test names (the bottom level) for content quality. That's `review-comment-drift` adjacent territory.
- It does not enforce a naming taxonomy across the codebase. Project taste varies; the audit surfaces collisions, not deviations from a fixed
  vocabulary.
- It does not run the suite. Pure static read.
