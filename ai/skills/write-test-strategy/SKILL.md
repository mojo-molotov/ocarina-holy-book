---
name: write-test-strategy
description: Produce (or refresh) the project's **test-strategy document** end-to-end — the artifact that catalogues scope, objectives, ISTQB-flavoured test types, per-feature coverage tables, the cycle/campaign/suite tree (as actually wired in Ocarina), pass/fail criteria, the known-gaps table, and the CI execution matrix. Generated, not invented: every row in the coverage tables traces back to a real `create_selenium_test(...)` in `tests/scenarios/`; every node in the tree comes from the `TestCycle → TestCampaign → TestSuite → Test` topology defined in the project's cycle file; every gap row comes from the FRD's known-bugs section and the project's gap inventory. Use when the user asks to build, rebuild, refresh, or audit the test-strategy doc; after a structural change (new test, renamed suite, new campaign, smoke-gate move); on first authoring; or as a pre-release readiness pass. A worked instance is `CURA_TEST_STRATEGY.md` in `ocarina-with-ai-example` — useful as a format reference; every project supplies its own facts. Surface as a proposal; never auto-commit; pair with `assess-test-base` (inventory) and `update-frd-and-tests` (when the strategy reveals an FRD gap).
---

# Write the test-strategy document

A test-strategy doc is the legible map of a test suite: scope, types, what's covered (per feature), how the cycle is shaped, what passes and what
stays red. It exists so a reviewer who hasn't run the suite can predict its outcome shape, and so a contributor adding tests knows which type box
theirs falls into.

The shape is the canonical one — nine sections, generated from the wired suite. A worked instance is `CURA_TEST_STRATEGY.md` in
<https://github.com/mojo-molotov/ocarina-with-ai-example>, produced empirically against that example; cite it as a reference, but every project
supplies its own facts.

**Generated, not invented.** Every row in §5 traces back to a real `create_selenium_test(...)`; every node in §6 comes from the wired cycle; every row
in §8 comes from the FRD's known-bugs section + the project's gap inventory. No phantom tests, no aspirational coverage. If the suite doesn't exercise
something, the doc doesn't claim it does.

**Surface, don't apply.** The skill produces the doc as a proposal; the user reviews and signs off before commit.

Default target: `TEST_STRATEGY.md` (or whatever filename the project picks — `<SUT>_TEST_STRATEGY.md` is the common shape) at the repo root. For a
different location, ask.

## What the doc contains

Nine sections, in this order. Numbering matters — readers cite by section.

| §   | Section                                 | Where the content comes from                                                                      |
| --- | --------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 1   | Scope                                   | FRD scope section / project README; user input for "out of scope"                                 |
| 2   | Test objectives                         | FRD goals + the project's gap-handling discipline                                                 |
| 3   | Test types                              | The ISTQB-flavoured taxonomy below — refined per project                                          |
| 4   | Interaction path coverage (dispatchers) | POM `_*_dispatchers: dict[str, Effect]` — list only if present                                    |
| 5   | Coverage                                | Every `create_selenium_test(...)` in `tests/scenarios/**` + every dataset case                    |
| 6   | Suite and campaign organisation         | `tests/cycles/<cycle>.py` — the `TestCycle(smoke_tests_campaigns=..., campaigns=...)` graph       |
| 7   | Pass / fail criteria                    | Categorical: green / intentional reds / cross-browser reds / environmental flakes. **No totals.** |
| 8   | Known gaps                              | FRD's known-bugs section joined with the project's gap inventory                                  |
| 9   | CI execution matrix                     | The e2e CI workflow file — browsers, fail-fast policy, artifact names                             |

## The type taxonomy (§3)

Six types in the canonical shape. Project may refine names; keep the discriminating questions.

| Type                                    | Result   | Discriminating question                                                                                    |
| --------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| Happy path                              | PASS     | Nominal flow, valid inputs, authenticated user. Verifies the correct output appears.                       |
| Unhappy path                            | PASS     | Invalid input or out-of-auth action. Test **passes** when the SUT correctly rejects.                       |
| Edge case / boundary                    | PASS     | Limits, surprising behaviour, ambiguous spec. Paired with an FRD note if the result is a gap.              |
| Business logic vulnerability / gap test | **FAIL** | SUT _should_ enforce X but doesn't. Test asserts the missing enforcement; **intentionally fails**.         |
| Exploratory / observed-behaviour        | PASS     | No requirement specified; the test documents what the SUT actually does. Always paired with an FRD update. |
| Permanent security regression           | mixed    | Guards against runtime/browser-version drift (e.g., BFcache, session handling). Never removed or skipped.  |

The discriminator that matters most: **unhappy path** passes when the SUT correctly rejects; **gap test** fails because the SUT _doesn't_ reject. Same
shape ("submit bad input → check rejection"), opposite outcome — and the doc must say which is which.

## Canonical source layout

A mature Ocarina suite tends to converge on this shape. The grep commands below assume it; adapt paths if the project diverges.

```
src/
├── constants/                          urls, credentials, transient_errors
├── pages/                              POMs (one file per page) + components/ for shared UI
│   └── <page>.py                       _<verb>_dispatchers: dict[str, Effect] declared here, if any
├── lib/
│   ├── connectors/test_steps/<feature>.py   thin closures around POM methods
│   └── ext/ocarina/adapters/...             optional project wrappers of Ocarina's TestSuite / TestCampaign
└── tests/
    ├── cycles/<cycle>.py               TestCycle(smoke_tests_campaigns=[...], campaigns=[...])
    ├── campaigns/<feature>.py          create_<feature>_campaign(...) factory → TestCampaign(name=, suites=[...])
    ├── suites/<feature>/<suite>.py     create_<suite>_suite(...) factory → TestSuite(name=, tests=[...])
    └── scenarios/
        ├── _fragments/                 reusable pre/post fragments
        └── <feature>/
            ├── <scenario>.py           one scenario per file; test = create_selenium_test(...) at the bottom
            └── datasets/<name>.py      Sequence[Case] tuples for data-driven families
```

Three structural facts the skill relies on, regardless of project naming:

1. **The project may wrap Ocarina's classes.** A local adapter (e.g. under `lib/ext/ocarina/adapters/`) wrapping `TestSuite` / `TestCampaign` is a
   common pattern. Adapters are transparent for topology purposes — same `name=`, same `suites=` / `tests=` semantics — but mean a literal-text grep
   for `TestCampaign(` and `TestSuite(` only finds the constructors inside the factory files, not in the cycle file. Follow imports.
2. **The cycle file calls factories, not constructors.** Walk the import graph: cycle → `create_<x>_campaign()` →
   `TestCampaign(name="...", suites=[create_<y>_suite(...), ...])` → `TestSuite(name="...", tests=[<test bindings>])` →
   `tests/scenarios/<feature>/<scenario>.py` → `<scenario> = create_selenium_test(name="...", ...)`.
3. **Tests bind at module level at the bottom of the scenario file.** Either `test_<x> = create_selenium_test(...)` (single test) or
   `<x>_tests = [create_selenium_test(name=<name-helper>(case), ...) for case in <cases>]` (data-driven). Suite files import these bindings and pass
   them in `tests=[...]`.

## Procedure

### Step 0 — Pre-flight

Confirm the source artifacts exist:

```bash
ls src/tests/cycles/                        # the cycle file(s)
ls src/tests/campaigns/                     # campaign factories
ls src/tests/suites/                        # suite factories
ls src/tests/scenarios/                     # every test the doc will cite
ls src/constants/transient_errors.py 2>/dev/null  # for §7 flake categorisation
ls IDENTIFIED_GAPS.md 2>/dev/null           # gap inventory
ls .github/workflows/*e2e*.yml 2>/dev/null  # CI matrix
```

If any is missing, ask the user where it lives or whether to skip that section. Don't fabricate.

If `assess-test-base` has not been run recently, run it first — it produces the inventory you'll reference in §5/§6.

### Step 1 — §6 first (the cycle tree)

Build §6 before §5. The tree from `src/tests/cycles/<cycle>.py` is the **structural truth**; §5's per-feature tables are then ordered to match it.

Open the cycle file. The constructor typically passes factory _calls_, not literal objects:

```python
return TestCycle(
    name=<CYCLE_NAME>,
    smoke_tests_campaigns=[create_<smoke_x>_campaign(drivers_pool=...)],
    campaigns=[create_<x>_campaign(drivers_pool=...), create_<y>_campaign(drivers_pool=...), ...],
    # mode=... — optional; default is fail-fast-on-first-smoke-campaigns-sequence-fail
)
```

Walk every factory called by the cycle:

```bash
# Cycle → campaigns (imports)
rg -n 'import create_\w+_campaign' src/tests/cycles
# Each campaign file → its TestCampaign(name="...", suites=[...]) literal
rg -nA 10 'def create_\w+_campaign' src/tests/campaigns
# Each suite factory → its TestSuite(name="...", tests=[...]) literal
rg -nA 20 'def create_\w+_suite' src/tests/suites
```

Pull `name=` and the `suites=` / `tests=` lists from each literal constructor. The list members are imports — that's the next level down. Recurse
until you hit `create_selenium_test(...)` calls (the leaves).

Render the tree as ASCII with smoke gate clearly separated from main:

```
<CYCLE_NAME> Cycle
  │
  ├─ Smoke gate (fail-fast — skips main run if this fails)
  │    └─ <smoke campaign name>
  │         └─ <suite name>
  │              └─ <test name from create_selenium_test(name=...)>
  │
  └─ Main (runs only if smoke passes)
       ├─ <campaign name>
       │    ├─ <suite name>          — <one-line tagline of contents>
       │    └─ <suite name>          — <one-line tagline>
       └─ …
```

Annotate each leaf with a short tagline. Don't enumerate every test name — that's §5's job.

If `mode=` is set on `TestCycle(...)` and is non-default (`fail-fast-on-first-smoke-campaigns-sequence-fail`), call it out:
_"`mode='wait-for-all-smoke-tests'` — all smoke campaigns attempt regardless of the first failing."_

### Step 2 — §5 (coverage tables, per feature)

One table per feature, in the order the features appear in §6. Each row is **one `create_selenium_test(...)`** — including each data-driven case (the
`Sequence[Case]` expands to N rows in the doc).

Schema:

| Scenario | Type | Expected result |
| -------- | ---- | --------------- |

Where:

- **Scenario** — the human-readable test name from `create_selenium_test(name="…")`. Quote verbatim.
- **Type** — one of the six in §3.
- **Expected result** — `PASS — <one-line reason>` or `**INTENTIONAL FAIL** — <gap reference>` or
  `PASS (firefox) / FAIL (chrome) — <BFcache or browser finding>`.

Enumerate every test, single and data-driven:

```bash
# Single tests — test_<x> = create_selenium_test(name="...", ...)
rg -nP 'create_selenium_test\(\s*\n?\s*name="([^"]+)"' src/tests/scenarios
# Data-driven families — list comprehension at the bottom of the scenario file
rg -n '\[\s*create_selenium_test\(' src/tests/scenarios
# Datasets that drive them — Sequence[Case] tuples
rg -n 'Sequence\[\w+Case\]' src/tests/scenarios/*/datasets
```

For each data-driven family:

1. Open the dataset module under `tests/scenarios/<feature>/datasets/<name>.py` and count the rows in the `Sequence[Case]` tuple.
2. Open the scenario module and find the name helper (often `_test_name(case)`) or the f-string used inside `create_selenium_test(name=...)`. Apply it
   to each case in order. Each becomes one §5 row.

For each row, read the scenario file's top docstring — it carries everything §5 needs already:

- **Flow:** arrow notation → confirms the test type (an arrow ending in `verify NOT <X> (intentional FAIL — …)` is a gap test; one ending in
  `verify <X>` is happy/unhappy).
- **Pre-fragments / Post-fragments:** lists the fragments wired in. Note for §5 if a row depends on something other than the default authentication
  fragment.
- **Body paragraph:** usually states the FRD §, the rationale, and the gap reference. Lift the gap citation directly.

Cross-check the row against the bottom of the scenario file: the literal `create_selenium_test(name="...", pre_test_scenarios_fragments=[...])` is
authoritative for the name and the wiring.

Add a §5 sub-table header per feature, in §6 order. The mapping from scenario-directory to campaign is derived from the suite factories — open each
`create_<x>_suite(...)` and look at which `tests/scenarios/<dir>/` modules it imports. Don't assume a directory naming convention; derive it.

### Step 3 — §1, §2 (scope, objectives)

Two paragraphs. Pull from the FRD's scope section and the project README. Ask the user for explicit out-of-scope items (performance, accessibility,
payment, etc.) — these usually aren't written down anywhere else.

**Out-of-scope is for surfaces the SUT actually has but the suite deliberately does not test — not for things the SUT doesn't have at all.** The trap,
especially for LLMs, is to leave the SUT and start enumerating what a product _of this kind_ usually has: a real healthcare-booking app would have
email/SMS notifications, payment, cancellation, an admin console, an API layer. That's category inference, not SUT analysis. CURA has none of those —
listing them as "out of scope" invents features the SUT doesn't ship, and tells the reader nothing about _this_ suite. The contrast in the worked
example: `email/SMS notifications` is wrong (CURA has no notification feature at all — it doesn't belong in §1 in any form); `accessibility` is right
(CURA renders real HTML with real form controls that _could_ be audited, but the suite is functional, so the exclusion is a real choice worth
surfacing).

The filter, in order:

1. **Does the SUT have this surface at all?** Open the deployed app, the FRD, the source. If no — the feature doesn't exist — omit it. Absence from §5
   already says "not tested"; saying "not in scope" adds nothing and tells a future reader the suite considered something it never could.
2. **If yes, does the FRD include it in scope but the suite deliberately exclude it?** That's the real out-of-scope candidate. Typical shapes: a
   performance dimension on a functional suite, an accessibility audit deferred to a specialist tool, an admin path the project owns but doesn't
   regress here.
3. **If you're inferring from "what an app like this should have", stop.** That's a category prior, not a SUT fact. Either verify the surface exists
   (then it's filter 2) or drop the item.

When in doubt, ask the user rather than invent. A short, SUT-faithful list beats a long, plausibility-padded one.

`Objectives` are typically: verify FRD requirements; verify rejection of invalid input; document gaps as failing tests. If the project has a different
stance (e.g., gaps tracked in Jira instead of failing tests), record that.

### Step 4 — §3 (test types)

Render the taxonomy table above. For each type, add a sentence specific to the project — what `unhappy path` _looks like_ in this SUT (form
validation? redirect? error toast?), what the gap-test convention is (dedicated exception type? specific timeout?), what the exploratory pattern is.

For business-logic-vulnerability / gap tests, include the **implementation rule** the project uses — typically a dedicated assertion helper with a
fixed timeout independent of `--wait-timeout`, so a gap fail is visibly distinct from a generic timeout. Document the helper's name and the timeout
constant. Without that detail, a reviewer can't tell a gap-test fail from a transient timeout.

### Step 5 — §4 (interaction path coverage), only if dispatchers exist

Dispatchers are declared in POM `__init__` as `self._<verb>_dispatchers: dict[str, Effect] = {"<path_name>": lambda: ..., ...}` and consumed by
`submit_<verb>()` via `random.choice(list(self._<verb>_dispatchers.values()))()`.

Grep:

```bash
rg -nP '_\w+_dispatchers\s*:\s*dict\[' src/pages
# For each match, the keys of the dict are the path names — extract them
rg -nA 20 '_\w+_dispatchers\s*:\s*dict\[' src/pages
```

If none: omit §4 entirely.

If present: one row per `(POM, method, paths)`. The path names come from the dict keys; render as a `/`-separated list. Schema:

| POM     | Method     | Paths                   |
| ------- | ---------- | ----------------------- |
| `<POM>` | `<verb>()` | `<path>` / `<path>` / … |

For each POM whose dispatcher set is smaller than the obvious enumeration would suggest (e.g., missing an Enter-on-input path), document _why_ —
typically because a widget on that input intercepts the interaction, with a dedicated test asserting the interception. Cite the test name; otherwise
the row reads as a coverage gap.

This section exists to forestall the misreading _"randomness in interaction = non-determinism in assertions"_. Add the explicit reassurance: _"the
outcome asserted is always deterministic; only the interaction path varies."_ Note the `--workers N` amplification: with N workers, each test runs N
times in the cycle and likely picks a different dispatcher per run.

### Step 6 — §7 (pass/fail criteria)

Categorical, not numeric. **Never** write a "N/M tests pass" total. `--workers N` clones single-test suites (the `[COPY N]` runs), so any raw count is
inflated, run-dependent, meaningless.

Four buckets:

1. **Everything passes on every browser except the two categories that follow** — enumerate the principal pass categories (happy paths, unhappy paths,
   edge cases, cross-feature flows, permanent security regression guards that are green).
2. **Intentional gap fails — red on every browser, by design** — one bullet per gap, with the FRD reference.
3. **Expected cross-browser reds** — per-browser per-test (e.g., red on browser A / green on browser B), each with the gap-inventory + FRD reference.
4. **Environmental flakes under parallel workers** — the shared-infrastructure contention, cold-start, driver-artifact entries the project has
   documented. Reference the gap inventory's environmental-artifact entries.

The flake categorisation in bucket 4 hinges on the project's `transient_errors` constant (typically `src/constants/transient_errors.py`): exceptions
listed there auto-retry, so a one-shot occurrence followed by a green retry is the expected shape. A failure that survives all retries with a known
transient signature is the documented artifact, not a regression. Cite the file in §7 so reviewers know which exceptions are retried.

Add `Note on …` paragraphs for any flake category that needs explanation (cold-start, browser-runtime quirk, infrastructure-side contention, etc.).
These are the dispatch lines a reviewer needs when they see a fail and want to know whether it's a known artifact or a regression.

### Step 7 — §8 (known gaps)

Join the FRD's known-bugs section with the project's gap inventory. Schema:

| Gap | Affected test | FRD ref |
| --- | ------------- | ------- |

Each gap row points at the failing test by exact `name=` string. Reviewers grep for the test name and find the gap; reviewers reading the test code
grep for the FRD ref and find the gap.

If a gap exists in the gap inventory but no failing test asserts it, flag for the user — the strategy doc shouldn't silently omit gaps the suite
doesn't yet cover.

### Step 8 — §9 (CI execution matrix)

Read the project's e2e CI workflow file:

```bash
yq '.jobs.*.strategy.matrix' .github/workflows/*e2e*.yml
```

Render as a table: Browser | Driver | Artifacts. Note `fail-fast: false` policy explicitly. Document the "**never collapse the matrix to a single
browser**" rule — browser-specific findings (BFcache restore, back-navigation, session-cookie handling) are precisely what the matrix exists to
surface.

### Step 9 — Review pass

Before surfacing to the user, walk every cross-reference:

- Every `name="…"` in a §5 row exists verbatim in a `create_selenium_test(name="...")` call (including the dataset-expanded names).
- The order of features in §5 matches the order of campaigns in §6.
- Every node in §6 matches what the cycle / campaign / suite factories actually wire (smoke gate, campaigns, suites, leaf tests).
- Every gap row in §8 has a corresponding failing test (or is flagged otherwise).
- Every FRD reference exists in the FRD.
- The `mode=` documented in §6 matches the cycle constructor (or is absent if the default is used).
- The dispatchers in §4 match the POMs (`_<verb>_dispatchers.keys()` from `__init__`).
- Every fragment cited in §5 exists in `tests/scenarios/_fragments/`.
- The transient-error categories in §7 match the exception tuple in the project's `transient_errors` constant.

A cross-reference miss is the failure mode of this skill — it produces a doc that _looks_ authoritative and isn't. Catch it here, before the user
reads it.

### Step 10 — Surface the diff

Output the proposed doc (or diff against the existing one). For each section, name the source artifact it was generated from and any uncertain calls —
`assess-test-base` style of inventory, not authoritative claims.

User signs off. Then commit.

## Re-running this skill

The doc drifts the moment the suite changes. Re-run when:

- A test is added, removed, or renamed.
- A suite or campaign is renamed, split, merged, or moved between smoke/main.
- `mode=` changes on the cycle.
- A dispatcher is added or removed.
- A gap is resolved (the gap test is reframed by `update-frd-and-tests`, then this skill refreshes §5 + §8).
- A new browser joins the CI matrix.
- An environmental flake is documented in the gap inventory.

A refresh need not rewrite the whole doc — surface the affected sections only.

## Worked example

`CURA_TEST_STRATEGY.md` in <https://github.com/mojo-molotov/ocarina-with-ai-example> is one full instance produced empirically against the CURA SUT —
useful as a shape reference for the nine sections (the ASCII tree in §6, the per-feature coverage tables in §5, the categorical pass/fail buckets in
§7, the gap table in §8). Treat it as a gold standard for _format_; the _facts_ in any project's strategy doc come from that project's own suite, FRD,
and gap inventory.

## What this skill does NOT do

- **It does not invent coverage.** Every claim traces to source. If §5 lists a test, the test exists in `tests/scenarios/`. Aspirational rows belong
  in `BACKLOG.md`, not the strategy doc.
- **It does not write tests.** New coverage gaps surfaced during the walk go to `extend-coverage`; the strategy doc only catalogues what's there.
- **It does not flip gap tests.** A failing test that surprises with a pass (or vice versa) routes through `update-frd-and-tests` and `empiricism` —
  not through editing the row.
- **It does not produce numeric totals.** `--workers N` saturation makes counts meaningless; the doc is categorical.
- **It does not modify the cycle topology.** The cycle file is the structural truth; the doc reflects it, not the other way around. Restructuring
  suites/campaigns is a separate edit, then re-run this skill.
- **It does not commit.** The doc is surfaced for review; the user signs off before any file is written.
