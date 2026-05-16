# Skills — index by family

Skills for working in any Ocarina-based browser test suite. Each entry below points to a `<skill-name>/SKILL.md`. Skills stay flat on disk (so
discovery keeps working); this document groups them by family for navigation.

These skills are couple-light by design — they lean on Ocarina (the framework), the browsers Ocarina drives (Firefox, Chrome, Edge, Safari), and
the host OSes (macOS, Windows, Linux). Everything else — the SUT's backend stack, the spec format (Markdown, Jira, Confluence, OpenAPI, PDF, JSON),
the project layout — is interoperable. Worked examples cite <https://github.com/mojo-molotov/ocarina-example> or
<https://github.com/mojo-molotov/ocarina-with-ai-example>; the framework itself is at <https://github.com/mojo-molotov/ocarina> and the docs at
<https://github.com/mojo-molotov/ocarina-holy-book>.

The prefix convention (`review-*`, `analyse-*`, `assess-*`, `pick-*`, `understand-*`) does most of the grouping at the filename level. The families
below add the prefix-less skills (ideation, refactoring, authoring, state-probing).

Conventions every skill in this directory shares:

- **Surface, don't apply.** The skill produces a report / catalogue / plan; the user signs off before any edit.
- **Empirical before assertive.** When a skill's recommendation rests on a SUT-behaviour claim, verify via `empiricism` / `write-a-probe` first.
- **Functional and static security only.** Per `CLAUDE.md` → *"Security testing is functional and static — never active"*. Every black-hat /
  attack-ideation skill respects this hard line.
- **Mtime, not filename.** All file-picking skills (`pick-*`) sort by modification time — UUID suffixes in screenshots / logs / reports are random.

## Review (static review)

Read the codebase or specs and surface findings; never edit.

- [review-type-ignore](review-type-ignore/SKILL.md) — audit `# type: ignore` comments, especially on Ocarina built-ins.
- [review-match-candidates](review-match-candidates/SKILL.md) — find `if/elif` chains that should become `match` statements.
- [review-unverified-transitions](review-unverified-transitions/SKILL.md) — `drive_page` transitions without a verify on the destination POM.
- [review-submit-dispatchers](review-submit-dispatchers/SKILL.md) — form-commits that should use random dispatcher selection.
- [review-comment-drift](review-comment-drift/SKILL.md) — comments that no longer match the code they annotate.
- [review-suite-stability](review-suite-stability/SKILL.md) — multi-replay × multi-browser run; per-test category audit against the strategy doc.
- [review-intent-collisions](review-intent-collisions/SKILL.md) — happy-path tests that collide with intentional-fail gap tests.
- [review-spec-gaps](review-spec-gaps/SKILL.md) — benevolent QA-style spec review; surface clarification questions.
- [review-report](review-report/SKILL.md) — classify every FAIL and SKIP in a single run report (body/setup/teardown × static/smoke-gate/setup-error/cycle-policy).
- [review-watcher-emissions](review-watcher-emissions/SKILL.md) — find watcher-emitted artifacts hiding in run output; emissions are always negative signals.
- [review-watcher-misuse](review-watcher-misuse/SKILL.md) — audit watcher callbacks for the negative-only convention.
- [review-compartmentalisation-leaks](review-compartmentalisation-leaks/SKILL.md) — literals (URLs, credentials, selectors, magic numbers) outside their canonical module.

## Analyse (diagnostic experiments)

Run a controlled experiment, observe, restore. Mandatory restore step in each.

- [analyse-flakiness](analyse-flakiness/SKILL.md) — widen the transient-error classifier; watch what still dies under retries.
- [analyse-fixture-flakiness](analyse-fixture-flakiness/SKILL.md) — instrument the setup/teardown boundary; reconstruct per-worker timelines.
- [analyse-watcher-flakiness](analyse-watcher-flakiness/SKILL.md) — eight failure shapes of Ocarina watchers; with/without × interval sweep.
- [analyse-screenshot-flakiness](analyse-screenshot-flakiness/SKILL.md) — visual comparison across runs; triage anomalies into `Watcher` / `match_page` / cross-reference paths.

## Black-hat (adversarial ideation)

Generate attack catalogues — every action through the normal UI, never injection / curl / proxy / DevTools manipulation.

- [business-attack-ideation](business-attack-ideation/SKILL.md) — volume / saturation / slot-hoarding / aggregate-harm scenarios.
- [incoherence-attack-ideation](incoherence-attack-ideation/SKILL.md) — each step legitimate, the set impossible (temporal / spatial / biographical / causal / quantitative / relational).
- [persistence-attack-ideation](persistence-attack-ideation/SKILL.md) — hardening through insistent legitimate retry; seven insistence dimensions.
- [permission-appropriateness-audit](permission-appropriateness-audit/SKILL.md) — is the SUT's access model itself appropriate, even when perfectly enforced?
- [bfcache-exposure-ideation](bfcache-exposure-ideation/SKILL.md) — back-button restores pre-access-change pages; a generic BFcache exposure pattern.
- [lateral-resource-ideation](lateral-resource-ideation/SKILL.md) — IDOR-spirited, address-bar-only; sibling-ID guessing through the URL.

## Comprehend (assessment & understanding)

Build / refresh a mental model — of the codebase, the ecosystem, the SUT's constraints, the framework.

- [assess-test-base](assess-test-base/SKILL.md) — catalogue of the existing test base across seven categories.
- [assess-ecosystem](assess-ecosystem/SKILL.md) — bounded public-research pass over eight ecosystem surfaces; token-budget-controlled.
- [understand-sut-constraints](understand-sut-constraints/SKILL.md) — map SUT-side bounds that constrain parallel-test safety; distributed mitigations only.
- [understand-ocarina](understand-ocarina/SKILL.md) — four-tier framework comprehension; Holy Book first.

## Pick (file selection)

Pick the right files from run output. Always mtime-sorted.

- [pick-screenshots](pick-screenshots/SKILL.md) — screenshots from `<gitignored>/screenshots/`.
- [pick-logs](pick-logs/SKILL.md) — log roots from `.ocarina_logs_<id>/`.
- [pick-reports](pick-reports/SKILL.md) — DOCX / JSON from `.reports/`.

## Author (workflows that produce code or durable artifacts)

End-to-end workflows. Each produces a deliverable (test, PR description, gap entry, repro guide, probe).

- [empiricism](empiricism/SKILL.md) — verify before encoding; never overwrite intentional-fail gap tests.
- [write-a-probe](write-a-probe/SKILL.md) — throwaway script in `<gitignored>/`, exact-target rule, deleted after finding lands.
- [write-test-strategy](write-test-strategy/SKILL.md) — produce the test-strategy doc end-to-end: scope, ISTQB-flavoured types, per-feature coverage tables, the cycle/campaign/suite tree, pass/fail criteria, known gaps, CI matrix. Generated from the suite, not invented.
- [extend-coverage](extend-coverage/SKILL.md) — six adjacency dimensions for finding uncovered cases.
- [update-frd-and-tests](update-frd-and-tests/SKILL.md) — spec change propagation; gap tests reframed, never silently flipped.
- [manual-reproduction-guide](manual-reproduction-guide/SKILL.md) — human-runnable browser repro; up to three layers.
- [manage-backlog](manage-backlog/SKILL.md) — `BACKLOG.md` schema; generate / ingest modes.
- [pr-report](pr-report/SKILL.md) — PR-type-aware report (refactor / test-strategy / bug fix / docs).

## Refactor

Surface refactor candidates; user applies.

- [refactor-fragmentation](refactor-fragmentation/SKILL.md) — extract `TestScenarioFragment`s after two gates (codebase size + DRY policy).
- [introduce-pom-retries](introduce-pom-retries/SKILL.md) — POM-level retries with the two-test split (first-try intentional fail + with-retries variant).

## State

Question the environment before assuming a result is meaningful.

- [question-state](question-state/SKILL.md) — nine surfaces of environmental state to interrogate before trusting a test outcome.

## Setup

Stand up or refresh the local working environment so the suite is runnable, lintable, and type-clean.

- [setup-environment](setup-environment/SKILL.md) — venv + dev tooling + `CLAUDE.local.md` driver paths + the `ruff` / `mypy` / `pre-commit` quality loop + a smoke-check of the runner.

## Cross-family dispatch (which skill follows which)

A few recurring chains:

- `review-report` → `analyse-flakiness` / `analyse-fixture-flakiness` / `analyse-screenshot-flakiness` / `write-a-probe` depending on incident class.
- `review-suite-stability` → `review-report` for the per-run unit, then `analyse-*` for chronic shapes.
- Black-hat ideation → `empiricism` to verify the SUT's current behaviour → `extend-coverage` to author the test.
- Spec change → `update-frd-and-tests` (spec doc first, tests follow, gap tests reframed not flipped).
- New flake suspect → `empiricism` → `write-a-probe` → finding lands in the gap inventory / scenario comment / spec doc → probe deleted.
- Any framework question → `understand-ocarina` (Holy Book first, then source / example clones).
