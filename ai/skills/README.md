# Skills — index by family

Skills for working in any Ocarina-based browser test suite. Each entry below points to a `<skill-name>/SKILL.md`. Skills stay flat on disk (so
discovery keeps working); this document groups them by family for navigation.

These skills are couple-light by design — they lean on Ocarina (the framework), the browsers Ocarina drives (Firefox/Chromium, Chrome, Edge,
Safari/WebKit), and the host OSes (macOS, Windows, Linux). Everything else — the SUT's backend stack, the spec format (Markdown, Jira, Confluence,
OpenAPI, PDF, JSON), the project layout, **and the driver adapter (Selenium or Playwright)** — is interoperable. Concrete examples in a skill use
whichever adapter the suite is wired on; driver-level mechanics (the wait API, selector form, submission primitives, CLI flags) live in
`CLAUDE.selenium.md` / `CLAUDE.playwright.md`, not in the skills. Worked examples cite <https://github.com/mojo-molotov/ocarina-example> or
<https://github.com/mojo-molotov/ocarina-with-ai-example> (Selenium) and <https://github.com/mojo-molotov/ocarina-with-playwright-example>
(Playwright); the framework itself is at <https://github.com/mojo-molotov/ocarina>, the reference docs at
<https://github.com/mojo-molotov/ocarina-holy-book>, and the ecosystem book (intent, cartography, philosophy) at
<https://github.com/mojo-molotov/from-ocarina-to-igor>.

The prefix convention (`review-*`, `analyse-*`, `assess-*`, `pick-*`, `understand-*`) does most of the grouping at the filename level. The families
below add the prefix-less skills (ideation, refactoring, authoring, state-probing).

Conventions every skill in this directory shares:

- **Surface, don't apply.** The skill produces a report / catalogue / plan; the user signs off before any edit.
- **Empirical before assertive.** When a skill's recommendation rests on a SUT-behaviour claim, verify via `empiricism` / `write-a-probe` first.
- **Functional and static security only.** Per `CLAUDE.md` → *"Security testing is functional and static — never active"*. Every black-hat /
  attack-ideation skill respects this hard line.
- **Mtime, not filename.** All file-picking skills (`pick-*`) sort by modification time — UUID suffixes in screenshots / logs / reports are random.
- **Diagrams are Mermaid, in the surfaced report, never committed.** Skills that emit a diagram (the `diagnose-*` pair, `assess-impact`, the
  `analyse-*` family, the attack-ideation skills) render it as Mermaid inside **the report the skill surfaces to you** — the skill's own Markdown deliverable (the
  `# … analysis` / catalogue it hands back), _not_ Ocarina's run artifacts in `.reports/` (DOCX proofs, JSON results). It is text, so diffable and
  regenerable. A diagram is never committed into the repo, where it would drift (per `review-comment-drift`); the durable artifacts are the findings
  the diagram summarises.

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
- [review-dead-code](review-dead-code/SKILL.md) — unused connectors / POMs / scenarios / suites / fragments / constants; per-finding choice between delete, incubate (`<source-root>/incubator/`), or keep — applied with dependency-tree preservation and the project's lint/format/type-check loop.
- [review-hierarchy-naming](review-hierarchy-naming/SKILL.md) — audit `TestCycle → TestCampaign → TestSuite → Test` naming for the lazy-naming antipattern where a child carries the parent's name (most often `Campaign("X") ⊃ Suite("X")`); flags exact / near-match / semantic-mirror pairs and proposes rename-or-flatten options. Surface only; user owns the rename.

## Analyse (diagnosis)

Diagnose a failure. **Two root-cause skills, deliberately separate** — `diagnose-root-cause` for a deterministic red, `diagnose-flake-root-cause` for
an intermittent one (a distribution-based discipline, not a single-run one) — sit in front of four controlled flakiness experiments (`analyse-*`:
observe, restore — mandatory restore step in each).

- [diagnose-root-cause](diagnose-root-cause/SKILL.md) — structured RCA for a **deterministic** red; re-derive don't inherit, the synthetic→real ladder, source read, probe confirmation, a causal-chain Mermaid diagram, root cause sorted into five buckets. Hands off to `diagnose-flake-root-cause` the moment a failure proves intermittent.
- [diagnose-flake-root-cause](diagnose-flake-root-cause/SKILL.md) — structured RCA for an **intermittent** failure (a flake); the distribution is the evidence — establish a failure rate, pin the signature, correlate, route to the right `analyse-*` experiment, raise the rate to confirm, classify into five flake buckets; causal diagram rooted at a trigger condition. The orchestrator of the `analyse-*` family.
- [analyse-flakiness](analyse-flakiness/SKILL.md) — widen the transient-error classifier; watch what still dies under retries; Mermaid classifier-outcome flowchart.
- [analyse-fixture-flakiness](analyse-fixture-flakiness/SKILL.md) — instrument the setup/teardown boundary; reconstruct per-worker timelines as a Mermaid `gantt`.
- [analyse-watcher-flakiness](analyse-watcher-flakiness/SKILL.md) — eight failure shapes of Ocarina watchers; with/without × interval sweep; Mermaid thread-interleaving sequence.
- [analyse-screenshot-flakiness](analyse-screenshot-flakiness/SKILL.md) — visual comparison across runs; triage anomalies into `Watcher` / `match_page` / cross-reference paths via a Mermaid decision tree.

## Black-hat (adversarial ideation)

Generate attack catalogues — every action through the normal UI, never injection / curl / proxy / DevTools manipulation.

- [business-logic-vulnerability-ideation](business-logic-vulnerability-ideation/SKILL.md) — volume / saturation / slot-hoarding / aggregate-harm scenarios.
- [incoherence-attack-ideation](incoherence-attack-ideation/SKILL.md) — each step legitimate, the set impossible (temporal / spatial / biographical / causal / quantitative / relational).
- [persistence-attack-ideation](persistence-attack-ideation/SKILL.md) — hardening through insistent legitimate retry; seven insistence dimensions.
- [permission-appropriateness-audit](permission-appropriateness-audit/SKILL.md) — is the SUT's access model itself appropriate, even when perfectly enforced?
- [bfcache-exposure-ideation](bfcache-exposure-ideation/SKILL.md) — back-button restores pre-access-change pages; a generic BFcache exposure pattern.
- [lateral-resource-ideation](lateral-resource-ideation/SKILL.md) — IDOR-spirited, address-bar-only; sibling-ID guessing through the URL.

## Comprehend (assessment & understanding)

Build / refresh a mental model — of the codebase, the ecosystem, the SUT's constraints, the framework — or map the blast radius of a change.

- [assess-test-base](assess-test-base/SKILL.md) — catalogue of the existing test base across seven categories.
- [assess-impact](assess-impact/SKILL.md) — forward impact analysis: given a change (SUT change / planned refactor / a `diagnose-*` shared-component cause), trace its blast radius through the dependency graph, classify each affected node (broken / stale claim / gap-test-may-flip / coverage-gap / smoke-gate crossing), render a Mermaid dependency-slice. The forward dual of the `diagnose-*` pair.
- [assess-ecosystem](assess-ecosystem/SKILL.md) — bounded public-research pass over eight ecosystem surfaces; token-budget-controlled.
- [understand-sut-constraints](understand-sut-constraints/SKILL.md) — map SUT-side bounds that constrain parallel-test safety; distributed mitigations when the fleet shares scarcity, worker-local in-memory only when it doesn't (and the keys + thread-safety gates pass).
- [understand-ocarina](understand-ocarina/SKILL.md) — framework comprehension routed by question class: the Holy Book for reference (what a primitive is), the `from-ocarina-to-igor` book for intent / ecosystem cartography / philosophy (why it's shaped this way), then the Ocarina source and the adapter-matched worked example for behaviour and shape.

## Pick (file selection)

Pick the right files from run output. Always mtime-sorted.

- [pick-screenshots](pick-screenshots/SKILL.md) — screenshots from the flat screenshot heap; inspects the latest `.ocarina_logs_*` root to segment the heap by run and contextualise each shot (fresh / earlier run / no log).
- [pick-logs](pick-logs/SKILL.md) — log roots from `.ocarina_logs_<id>/`.
- [pick-reports](pick-reports/SKILL.md) — DOCX / JSON from `.reports/`.

## Author (workflows that produce code or durable artifacts)

End-to-end workflows. Each produces a deliverable (test, PR description, gap entry, repro guide, probe).

- [empiricism](empiricism/SKILL.md) — verify before encoding; never overwrite intentional-fail gap tests.
- [write-a-probe](write-a-probe/SKILL.md) — throwaway script in `<gitignored>/`, exact-target rule, instrument matched to the question (Selenium / raw HTTP / CDP / Playwright — server-rendered or reactive SPA), deleted after finding lands.
- [write-test-strategy](write-test-strategy/SKILL.md) — produce the test-strategy doc end-to-end: scope, ISTQB-flavoured types, per-feature coverage tables, the cycle/campaign/suite tree, pass/fail criteria, known gaps, CI matrix. Generated from the suite, not invented.
- [plan-test-effort](plan-test-effort/SKILL.md) — first-pass, naïve test-effort plan: requirements graded critical / major / minor, lightweight risk register (likelihood × impact, three buckets), relative effort weights (S / M / L), open questions for the deeper pass. Explicitly labelled as a first cut; precursor to deeper methods (ISO 31000 risk-based, ISO 25010 quality-model, FMEA, capacity modelling).
- [extend-coverage](extend-coverage/SKILL.md) — six adjacency dimensions for finding uncovered cases.
- [update-frd-and-tests](update-frd-and-tests/SKILL.md) — spec change propagation; gap tests reframed, never silently flipped.
- [manual-reproduction-guide](manual-reproduction-guide/SKILL.md) — human-runnable browser repro; up to three layers.
- [manage-backlog](manage-backlog/SKILL.md) — `BACKLOG.md` schema; generate / ingest modes.
- [pr-report](pr-report/SKILL.md) — PR-type-aware report (refactor / test-strategy / bug fix / docs).

## Refactor

Surface refactor candidates; user applies.

- [refactor-fragmentation](refactor-fragmentation/SKILL.md) — extract `TestScenarioFragment`s after two gates (codebase size + DRY policy).
- [introduce-pom-retries](introduce-pom-retries/SKILL.md) — POM-level retries as a separate `_with_retries` wrapper method (the `ocarina-example` pattern) over an idempotent base operation, with the two-test split (first-try intentional fail + with-retries variant).

## State

Question the environment before assuming a result is meaningful.

- [question-state](question-state/SKILL.md) — nine surfaces of environmental state to interrogate before trusting a test outcome.

## Setup

Stand up or refresh the local working environment so the suite is runnable, lintable, type-clean, and the skills invokable from Claude Code.

- [setup-environment](setup-environment/SKILL.md) — venv + dev tooling + driver-adapter choice (Selenium or Playwright, both shipped) + the Ocarina skill battery copied into Claude Code's skills directory + the suite's adapter-resolved `CLAUDE.md` assembled (core + chosen appendix + the `CLAUDE.profile.md` engagement appendix if `profile-environment` produced one, regenerable) + `CLAUDE.local.md` driver paths + verify/create the strict `ruff` (`pyproject.toml`), `mypy` (`mypy.ini`), and `.pre-commit-config.yaml` config of the worked examples + the `ruff` / `mypy` / `pre-commit` quality loop + a smoke-check of the runner.
- [profile-environment](profile-environment/SKILL.md) — profile the **engagement envelope** (the latitude the human grants the LLM) across seven dimensions — source access, live-system probing, data sensitivity, egress & confidentiality, the security-testing ceiling, autonomy & approval cadence, repo/CI/PR change surface — and emit a tracked `CLAUDE.profile.md` appendix `setup-environment` concatenates into `CLAUDE.md`. A **ratchet toward restriction**: only ever tightens the Holy Book's max-latitude defaults (open-source CURA demo) and the security hard line, never loosens them. Run at the start of any engagement that isn't the open public-demo case (a client site, an internal app, an NDA, live PII).

## Run

Surface the pre-run choices before a local dispatch; compose the command, hand it back.

- [propose-visual-review](propose-visual-review/SKILL.md) — offer `--not-headless` vs headless (CI-shaped) before a run, with the trade-off and what to watch for during a headed run.

## Cross-family dispatch (which skill follows which)

A few recurring chains:

- `review-report` → `diagnose-root-cause` for a deterministic body-failure red, `diagnose-flake-root-cause` for an intermittent one; the flake skill then orchestrates the `analyse-*` experiments and `write-a-probe` confirms any hypothesis.
- `review-suite-stability` → `review-report` for the per-run unit → `diagnose-root-cause` for a surprise red that survives re-runs, `diagnose-flake-root-cause` for one that doesn't.
- Diagnosing a red — pick by determinism: deterministic → `diagnose-root-cause` (re-derive, synthetic→real ladder, five-bucket verdict); intermittent → `diagnose-flake-root-cause` (failure rate, signature, correlation, five flake buckets — it drives the `analyse-*` experiments). Each hands off to the other if Step 0's verdict flips; user-facing findings go to `update-frd-and-tests`.
- Direction of travel — `diagnose-*` walks the dependency graph **backward** (symptom → cause); `assess-impact` walks it **forward** (change → blast radius). A `diagnose-*` cause localized to a shared component hands off to `assess-impact` to scope how far it contaminates.
- Before a refactor, or after a SUT change → `assess-impact` (trace the blast radius) → per affected node: `empiricism` / `write-a-probe` (stale claim), `update-frd-and-tests` (gap-test may flip), `extend-coverage` (new coverage gap), `review-dead-code` (orphaned node).
- Black-hat ideation → `empiricism` to verify the SUT's current behaviour → `extend-coverage` to author the test.
- Spec change → `update-frd-and-tests` (spec doc first, tests follow, gap tests reframed not flipped).
- New flake suspect → `diagnose-flake-root-cause` (failure rate → signature → correlate → routed `analyse-*` experiment) → `write-a-probe` to confirm by moving the rate → finding lands in the gap inventory / scenario comment / spec doc → probe deleted.
- Any framework question → `understand-ocarina` (routed by class: Holy Book for reference, the `from-ocarina-to-igor` book for intent / cartography, then source / adapter-matched example clones).
- Hygiene pass / pre-release pruning → `assess-test-base` (catalogue) → `review-dead-code` (audit unused connectors / POMs / scenarios / fragments / constants) → per finding: delete or move to `<source-root>/incubator/`.
- Local environment bring-up → `setup-environment` (venv + tooling + skill-battery install into Claude Code + driver adapter choice + `CLAUDE.local.md` + strict `ruff`/`mypy`/pre-commit config + quality loop).
- Engagement isn't the open public demo (client site / internal app / NDA / live PII) → `profile-environment` (seven-dimension latitude interview, emits `CLAUDE.profile.md`) → `setup-environment` Step 7 concatenates the profile appendix into `CLAUDE.md`. Re-run profiling and Step 7 when the engagement's terms change (staging → prod, demo data → real, an NDA lands).
- About to dispatch a run → `propose-visual-review` (headed vs headless choice, command composed, user runs).
- Inspecting run output → `pick-screenshots` always reaches into `pick-logs`' territory: the screenshot folder is a flat heap, so the latest `.ocarina_logs_*` root is what segments it by run and contextualises each shot. Picking screenshots without checking fresh logs gives recency but not meaning.
