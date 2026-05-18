---
name: review-dead-code
description:
  "**Review for dead code in an Ocarina suite** — connectors no scenario calls, POMs no scenario constructs, scenarios no suite wires in, tests no
  campaign / cycle picks up, fragments no `pre_test_scenarios_fragments` / `post_test_scenarios_fragments` references, datasets no factory consumes,
  constants nothing imports, helpers nothing calls. The skill grep-walks the source tree (default `src/`; detected from project config when present),
  classifies every unreferenced symbol by kind, surfaces its internal dependency tree (functions / classes / constants it transitively pulls in from
  the same project), and asks the user — per finding — for one of three motions: **delete**, **incubate**, or **keep**. _Delete_ removes the symbol
  and its now-orphan project-internal dependencies (after a second confirmation). _Incubate_ moves the symbol plus its full project-internal
  dependency tree into `<source-root>/incubator/`, rebuilds the imports so the moved code is self-contained, and cleans up the imports left orphaned
  in the original module. _Keep_ records the decision and moves on. After every applied motion the skill re-runs the project's lint / format /
  type-check loop (Ruff + mypy by default, the project's actual tools when configured otherwise) and reports green/red. Use whenever the user asks to
  audit dead code, find unused connectors / POMs / fragments / tests / constants, prune the codebase, prepare an incubator pass, or harden before a
  release."
---

# Review dead code — surface unused code, then delete or incubate it

A review-with-applied-motion skill. The static read identifies every project-internal symbol nothing references; the applied half moves chosen
findings into `<source-root>/incubator/` (or deletes them) while keeping the dependency tree intact, the imports clean, and the lint / type-check loop
green.

The principle this skill enforces lives in `CLAUDE.md` → _"No dead connectors. A connector function must be used in at least one scenario; speculative
ones are caught in review."_ This skill generalises that rule across every kind of asset an Ocarina suite carries.

`incubator/` is not deletion. It is the project's _"in preparation, not yet wired"_ shelf — code that may earn its way back into the suite later but
doesn't justify a place in the live tree today. Putting code into `incubator/` is a way to say _"I'm not ready to throw this away, but it's not part
of the system right now"_ without leaving orphans inside `src/`.

The skill is reasonably aggressive about surfacing candidates and conservative about applying motions: every move and every delete is gated on
explicit user approval.

## Source-root resolution

The skill targets the project's source root. Resolution order:

1. **Explicit user argument** — if the user names a directory, use it.
2. **Project config** — read `pyproject.toml` (`[tool.ruff] src = [...]`, `[tool.setuptools] packages.find.where = [...]`, `[tool.hatch.build]`,
   `[tool.poetry]`, `[tool.mypy] files = ...`), `setup.cfg`, `setup.py`, `package.json` for non-Python tooling. First match wins.
3. **Default** — `src/`.

`<source-root>/incubator/` is the move target. Create it on first incubation; gitignore nothing (the incubator is committed — its visibility is the
point). If the project already has an `incubator/` elsewhere, surface the discrepancy and ask before creating a second one.

## Tooling resolution

The quality loop the skill runs after each applied motion is the project's loop, not a hardcoded one. Resolution order:

| Tool kind    | Default                                    | Detected via                                                                                                                                 |
| ------------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Linter       | `ruff check`                               | `pyproject.toml` `[tool.ruff]`, `.ruff.toml` → Ruff. `pyproject.toml` `[tool.flake8]` / `.flake8` → flake8. `setup.cfg` `[pylint]` → pylint. |
| Formatter    | `ruff format`                              | `pyproject.toml` `[tool.ruff.format]` → Ruff. `pyproject.toml` `[tool.black]` / `black` in dev deps → Black. `[tool.isort]` → isort follows. |
| Type checker | `mypy`                                     | `pyproject.toml` `[tool.mypy]` / `mypy.ini` → mypy. `[tool.pyright]` / `pyrightconfig.json` → pyright. `[tool.pyre]` → Pyre.                 |
| Pre-commit   | `pre-commit run --all-files` if configured | `.pre-commit-config.yaml` present.                                                                                                           |

If the project uses something else (`pylint`, `Pyright`, `Black`, `isort`, …), use it. The skill's contract is _"the code that comes out passes the
project's quality loop"_, not _"the code passes Ruff and mypy"_.

If no quality loop is configured at all, surface that as a finding before applying any motion and ask whether to proceed without verification.

## The seven kinds of dead

For each kind: what the canonical home is, what "dead" looks like, how to spot it. The list is Ocarina-shaped but the detection generalises — a Django
view nobody routes, a React component nobody renders, a constant nothing imports all read the same way against this taxonomy.

### 1. Dead connector

A connector function under `src/connectors/` (or the project's equivalent) called by no scenario, fragment, or test.

- **Detection**:
  ```bash
  # List every connector function defined
  grep -rnE "^def [a-z_]+\(" src/connectors --include="*.py"
  # For each <fn>, find call sites
  grep -rn "\b<fn>\b" src --include="*.py"
  ```
- **Anchored by**: `CLAUDE.md` → _"No dead connectors"_.

### 2. Dead act / step helper

A helper that builds an `act(...)` chain, exposed for reuse, that no `drive_page` calls.

- **Detection**: same shape as dead connector; the home is `src/connectors/test_steps/` or wherever the project keeps step helpers.

### 3. Dead POM

A page object class in `src/pages/` that no scenario constructs and no other POM composes / inherits from.

- **Detection**:
  ```bash
  # List POM classes
  grep -rnE "^class [A-Z][A-Za-z]+\(.*POMBase" src/pages --include="*.py"
  # Find construction sites for each
  grep -rn "\b<ClassName>(" src --include="*.py"
  ```
- **Caveat**: a base / mixin POM that exists only to be subclassed counts as "live" if any concrete POM subclasses it.

### 4. Dead scenario

A scenario file whose `create_selenium_test(...)` outputs aren't unpacked into any `TestSuite.tests=[...]`.

- **Detection**:
  ```bash
  # Tests created
  grep -rnE "= create_selenium_test\(" src/tests/scenarios --include="*.py"
  # Where they're collected
  grep -rn "tests=\[" src/tests --include="*.py"
  ```
- **Caveat**: a data-driven family (list comprehension producing N tests) is one symbol from the wiring side — check the list name, not each test.

### 5. Dead suite / campaign / cycle

A `TestSuite`, `TestCampaign`, or `TestCycle` not referenced by anything higher in the hierarchy. A `TestCycle` not invoked from `main.py` (or the
project's launcher) is dead at the top.

- **Detection**: traverse the hierarchy from `main.py` outward; anything unreached is dead.

### 6. Dead fragment

A scenario fragment in `src/tests/scenarios/_fragments/` (or equivalent) not listed in any `pre_test_scenarios_fragments=` or
`post_test_scenarios_fragments=`.

- **Detection**:
  ```bash
  grep -rnE "^def [a-z_]+\(" src/tests/scenarios/_fragments --include="*.py"
  grep -rn "pre_test_scenarios_fragments\|post_test_scenarios_fragments" src --include="*.py"
  ```

### 7. Dead constant / dataset / helper

A name in `src/constants/`, `src/.../datasets/`, or any utility module that nothing imports.

- **Detection** (Python): `vulture src/` flags unused names quickly; cross-check each hit (vulture has known false positives on Selenium / dynamic
  dispatch). Without `vulture`, fall back to:
  ```bash
  grep -rnE "^[A-Z_]+ = " src/constants --include="*.py"
  # For each <NAME>, look for imports / references
  grep -rn "\b<NAME>\b" src --include="*.py"
  ```

## Procedure

### Step 1 — Resolve source root and tooling

Apply the resolution rules above. Surface both decisions in the audit header so the user can correct them before any motion is applied.

### Step 2 — Walk the seven kinds

For each kind:

- Run the detection grep (or `vulture` for the catch-all kind).
- Filter false positives: names referenced via `__all__`, dynamic `getattr`, string-based plugin registries, anything imported in a `TYPE_CHECKING`
  block but used at runtime in a stub, anything called from `main.py` indirectly.
- Capture each true positive as `(file:line, kind, symbol, dependency tree)`.

The dependency tree for a symbol is the set of project-internal names it transitively imports / calls — anything that, if the symbol moves to
`incubator/`, must move with it to keep the moved file standalone. External dependencies (stdlib, `selenium`, `ocarina`, `requests`) do **not** belong
in the tree — they remain importable from `incubator/` exactly as they were from `src/`.

Build the tree by walking imports (AST or `grep` on `from src.* import` / `import src.*`) one hop at a time, recording each project-internal name the
symbol pulls in, then recursing into each of those names' own dependencies. Stop at:

- Names that are referenced elsewhere in `src/` _outside the dead set_ — those are shared, they don't move.
- External imports (above).
- The symbol itself (don't recurse infinitely on self-reference).

A symbol whose tree contains a shared name needs special handling: the shared name **stays in `src/`**, and the moved file imports it back from
`src.<canonical-path>` (re-pointed if the canonical path itself moves later). Surface this in the per-finding report so the user understands the shape
of the move.

### Step 3 — Surface the audit

Use this template:

```markdown
# Dead-code audit — <project-name> (<date>)

## Resolved targets

- Source root: `<path>` (resolved from: <explicit / pyproject.toml `[tool.X]` / default>).
- Incubator target: `<source-root>/incubator/` (<exists | will be created on first motion>).
- Quality loop: <ruff format && ruff check && mypy | the project's actual loop>.

## Findings

### Dead connectors

- `src/connectors/<file>.py:<line>` — `<fn name>`
  - **Dependency tree (internal to project)**:
    - `src/connectors/<other>.py:<line>` — `<helper>` (only this dead symbol calls it; would move with).
    - `src/constants/<file>.py:<line>` — `<CONSTANT>` (shared with `src/tests/scenarios/<file>.py`; stays in place, moved file imports back).
  - **Recommendation**: <delete | incubate>. Reasoning: <one line>.

### Dead POMs

- ...

### Dead scenarios

- ...

### Dead suites / campaigns / cycles

- ...

### Dead fragments

- ...

### Dead constants / datasets / helpers

- ...

## False positives reviewed

- (Optional — items the detection flagged that turned out to be live via dynamic dispatch / plugin registration / `TYPE_CHECKING` stub.)

## Summary

- Total candidates: N
  - Dead connectors: A · POMs: B · Scenarios: C · Suites/campaigns/cycles: D · Fragments: E · Constants/datasets/helpers: F · Other: G
- Recommended motions: <X delete · Y incubate · Z keep-for-review>
```

Print the audit. Do **not** start applying motions yet.

### Step 4 — Ask, per finding, for the motion

For each finding the audit surfaced (in the order shown), prompt the user with the three options:

- **delete** — remove the symbol and any project-internal dependencies that become unreferenced after its removal. Requires a second confirmation
  before the file edits.
- **incubate** — move the symbol plus its full project-internal dependency tree into `<source-root>/incubator/`, mirroring the original module layout
  (e.g. `src/connectors/foo.py` → `src/incubator/connectors/foo.py`). Show the dependency tree from Step 2 alongside the prompt so the user sees what
  travels with the move.
- **keep** — record the decision (no edit). Useful for symbols that vulture / grep flagged but the user knows are about to be wired in by an in-flight
  branch.

Batch the prompts if the user prefers ("delete all dead constants; incubate everything else; let me eyeball POMs one by one"). Default is per-finding.

### Step 5 — Apply each chosen motion

#### Incubate

1. Create `<source-root>/incubator/` if it doesn't exist. Mirror the path structure under it (`src/connectors/foo.py` →
   `src/incubator/connectors/foo.py`).
2. Move the symbol's source code into the new file. If the dead symbol shares its original file with live symbols, **excise** it rather than moving
   the whole file: take only the dead symbol's definition (plus its own helpers from Step 2 that travel with it). The other contents of the original
   file stay where they are.
3. For each project-internal dependency the symbol pulled in:
   - If the dependency is shared with live code (Step 2 marked it as such), the moved file imports it back from its original canonical path
     (`from src.constants.urls import LOGIN_URL`).
   - If the dependency is itself dead and travels with the move, place it in the matching incubator location and re-point the moved file's import to
     the new path (`from src.incubator.connectors.helpers import _build_dispatcher`).
4. In the original file (the one the dead symbol was excised from), remove any imports that are now unused. Run `ruff check --select F401 --fix` if
   Ruff is the configured linter; otherwise apply the equivalent for the project's tool.
5. Run the project's full quality loop (Step 1 resolution). If anything fails, **stop**: report the failure to the user and ask whether to back out
   the move or fix forward. Do not paper over a failure with `# type: ignore` or `# noqa` — those are forbidden as fix-by-suppression per
   `review-type-ignore`.
6. Run the project's formatter (`ruff format <source-root>` by default).
7. Confirm to the user: paths moved, paths edited, quality loop result.

#### Delete

1. Show a final diff-shaped preview: the file edits the delete will produce (including any project-internal dependencies that become orphaned and
   would also be deleted in the same pass). Ask for explicit confirmation.
2. Remove the symbol's definition. Remove any project-internal dependency that is now unreferenced anywhere (recurse: a freshly-orphaned helper that
   itself referenced other now-orphan helpers, delete them too).
3. Clean up orphaned imports in any file the deletion touched (same `--select F401 --fix` motion, or the project equivalent).
4. Run the project's quality loop. If it fails, **stop** and ask. Do not suppress.
5. Run the project's formatter.
6. Confirm to the user: paths edited / removed, quality loop result.

#### Keep

Record the decision in the audit's session log (kept in-conversation; this skill writes no durable artifacts unless the user asks). Move to the next
finding.

### Step 6 — Summarise

Print one final report:

```markdown
## Dead-code review — applied motions

- Deleted: N files / M symbols.
- Incubated: N files / M symbols moved to `<source-root>/incubator/`.
- Kept (for review): N symbols.
- Quality loop after all motions: <PASS | FAIL — details>.
- Net delta: +A / −B lines, +C / −D files.
```

If anything failed mid-way, the report names exactly where and what the user needs to look at next.

## Hard rules

- **Static review precedes any motion.** The audit (Steps 1–3) always runs first and is shown to the user before a single edit. No fast-path.
- **Never apply a motion without explicit user approval for that finding.** Batch consent is fine if the user asks for it; silent batching is not.
- **Show the dependency tree before asking about an incubate motion.** Moving a symbol without surfacing what travels with it sets the user up for
  surprises.
- **Don't break the dependency tree.** If a symbol moves to `incubator/`, everything it pulls in either moves with it (when private to the move) or
  stays put and is imported back (when shared with live code). Never move a symbol and leave it referencing a path that no longer resolves.
- **Clean up orphan imports in the source file.** When a symbol leaves a shared file, the imports it pulled in stop being used. Remove them as part of
  the same motion; the file the symbol left behind must come out clean.
- **Respect the project's quality loop.** Whatever lint / format / type-check tools the project configures, run them after each motion. Failure stops
  the motion and surfaces to the user — no suppressions, no `# noqa`, no `# type: ignore` patched in to "make it pass".
- **`incubator/` is committed.** It's a visible part of the project, the opposite of `<gitignored>/`. The point is that contributors see what is
  brewing.
- **Don't grow the incubator into a graveyard.** If the user is incubating something they describe as _"I'll probably delete it later"_, push back —
  delete now is honest; incubate now is hoarding. The skill can name the question; the user decides.
- **Don't move tests into the incubator naively.** A test in `incubator/` is no longer collected by any cycle / campaign / suite. That's the point of
  moving it, but make sure the user understands the test stops running. Surface this explicitly when prompting on a dead test or scenario.
- **Don't auto-restore code from `incubator/`.** Resurrecting incubated code back into live `src/` is a separate, user-driven motion. This skill
  shelves; it does not unshelve.

## Cross-references

- `CLAUDE.md` → _"No dead connectors"_ rule (this skill generalises it across every kind of asset).
- Sister review skills: `review-compartmentalisation-leaks` (literals out of their canonical module), `review-type-ignore` (suppressions on the
  framework surface), `review-comment-drift` (stale comments).
- Adjacent comprehension: `assess-test-base` (the catalogue this skill prunes from), `understand-ocarina` (so a "dead" framework primitive isn't
  misread as project dead).
- Sister refactor skills: `refactor-fragmentation` (extracting a fragment often leaves the original block dead — feed straight into this skill);
  `introduce-pom-retries` (the two-test split sometimes orphans the first variant — same).
- After a motion is applied, the next runtime check is the project's quality loop (resolved per Step 1); behavioural verification on the next cycle is
  `review-report` territory.

## When to run this skill

- Periodically as part of a hygiene pass — once a refactor settles, dead branches often remain.
- Before a release — clean trees ship better changelogs.
- After a feature is descoped or rerouted — symbols built for the old shape become candidates.
- After a long refactor with many in-flight pieces — the unfinished branches often leave half-wired connectors / POMs / fragments behind.
- Onboarding — a new contributor reads `src/` and trips on dead code; pruning it first lowers the cognitive cost.

You may also run it without prompting if a review reveals an obviously-unreferenced connector or POM — confirm with the user before starting the full
audit.

## What this skill does NOT do

- It does not delete or move anything without explicit per-finding (or per-batch) approval.
- It does not suppress lint / type-check failures to force a motion through. A failing quality loop after a motion stops the motion.
- It does not gitignore `incubator/`. Visibility is the point.
- It does not auto-restore incubated code back into the live tree.
- It does not run the test suite after a motion. The quality loop covers static correctness; behavioural verification is the user's motion (and on a
  cycle whose tests just lost a fragment / scenario, the right next step is `review-report` on the next run).
- It does not audit deprecated public APIs of the framework (Ocarina) — the framework's own dead code is out of scope; this skill is suite-local.
- It does not include cross-repo / multi-repo dead-code analysis. One source tree per run.
- It does not move test artifacts (DOCX, JSON, logs, screenshots) — those live under `<gitignored>/` and are managed by `pick-*`.
