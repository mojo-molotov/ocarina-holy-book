---
name: assess-test-base
description: Produce a structured **inventory of the test base** — every artifact in this repo (and adjacent — SUT source, deployed app, user-facing docs if any) that a test author can ground new tests on. Walk the specs (FRD, strategy, gaps), the existing test code (scenarios, POMs, connectors, fragments, datasets, the cycle/campaign/suite topology), the SUT artifacts (GitHub PHP source, the live deployment, rendered HTML), the project conventions (`CLAUDE.md`, `README.md`), the constants/configs (URLs, credentials, transient errors), the run history (reports, logs, screenshots), and any external resources (user manuals, help docs — none here, but the slot exists). Produce a catalog: per source, what it contains, how a test author uses it. Use whenever the user asks to inventory the test base, onboard a contributor, plan a test pass, do a release-readiness survey, or answer "what do we have to work from?". Surface gaps in the inventory (sources that *should* exist for this project but don't yet) without inventing them.
---

# Assess test base — inventory of everything new tests can ground on

A snapshot skill. Walks every source of information a test author can use to ground new tests, summarises what each one contains, and notes how it
feeds the authoring loop. The output is a structured catalog — not an audit; this skill flags what's _there_, not what's wrong.

Two by-products:

- **Onboarding artifact.** A new contributor reads it once and knows where to look for everything.
- **Coverage-planning input.** The author scanning for "what should we cover next?" (see `extend-coverage`) reads the catalog first to know what facts
  are already documented.

Default target: this repo (the project root + `skills/` + the GitHub-source links for CURA). For a different project, ask the user.

## What goes in the inventory

Seven categories, in order. Each section names the artifact, summarises what's in it, and points at how it's used.

### 1. Specs

| Artifact                | What it is                                                                                                                                                                                             | How to use                                                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CURA_FRD.md`           | Reconstructed functional requirements (pages, element IDs, URL map, business rules, §9 known bugs). AI-generated from PHP + live exploration; treat as a test artifact, not ground truth.              | Source of element IDs (POM selectors), URL paths, expected business rules, intentional-fail gap inventory. Read before writing or modifying tests. |
| `CURA_TEST_STRATEGY.md` | Strategy, taxonomy (happy path / unhappy path / edge case / gap / exploratory), the §5 coverage tables, §6 cycle/campaign/suite tree, §7 expected outcome categories (no totals), §8 known-gaps table. | Read to understand intent before adding tests. The audit `review-suite-stability` reads its §7 each run.                                           |
| `IDENTIFIED_GAPS.md`    | Source-cited technical inventory of CURA defects + browser-behaviour findings + test-env artifacts (`G-*`, `B-*`, `A-ENV-*`). Each entry pairs symptom with PHP/probe evidence.                        | Read when working on a gap test or when a result surprises. Add entries on new findings; remove on CURA-side resolution.                           |

### 2. Existing test code

Walk it bottom-up — connectors first (what's possible), POMs second (what's modelled), scenarios third (what's exercised), suite/campaign/cycle
topology last (how it's wired).

| Artifact                                  | What it is                                                                                                                                                                          | How to use                                                                                                                                                                                      |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/pages/**/*.py`                       | POMs (`POMBase` + `SeleniumTitleMixin`). Each POM declares selectors at the top, then methods. `pages/components/` for shared UI (Sidebar).                                         | Source of: every available element interaction; selectors and their stable names; the dispatcher pattern (`_submit_dispatchers`). New tests reach for existing POM methods first.               |
| `src/lib/connectors/test_steps/**/*.py`   | Thin action wrappers around POM methods, in a closure pattern. One file per POM.                                                                                                    | The vocabulary of `act(pom, connector)`. New scenarios compose from connectors; no dead connectors allowed.                                                                                     |
| `src/tests/scenarios/_fragments/auth.py`  | Reusable pre/post-test fragments (currently: `login_as_demo_user`).                                                                                                                 | Pre/post-fragments for `create_selenium_test`. Extract a new fragment only when 3+ scenarios share the same block.                                                                              |
| `src/tests/scenarios/**/*.py`             | One scenario per file (except data-driven families). Each scenario builds `list[drive_page(...)]` with `act()` chains. Top docstring lists the flow as arrows + pre/post-fragments. | Source of: which flows are tested; the canonical patterns for write-up. New tests mirror the closest existing one's shape.                                                                      |
| `src/tests/scenarios/**/datasets/**/*.py` | Frozen dataclass + `Sequence[Case]` tuples for data-driven test families (`booking_cases`, etc.).                                                                                   | Adding a new case to an existing dataset is the cheapest way to add coverage in the same flow shape. Per `CLAUDE.md` → "Datasets are authoring decisions", any addition is surfaced for review. |
| `src/tests/suites/**/*.py`                | Suites — collections of tests with names and the drivers pool.                                                                                                                      | Source of: which suites exist and what they contain. New tests wire into the closest-fit suite.                                                                                                 |
| `src/tests/campaigns/**/*.py`             | Campaigns — collections of suites.                                                                                                                                                  | Source of: the feature-shaped grouping (Authentication, Appointments, Profile, User journeys, Prerequisites/Smoke).                                                                             |
| `src/tests/cycles/e2e.py`                 | The cycle (smoke gate + main). The single entry point used by `main.py`.                                                                                                            | Read to understand the smoke/main split. Adding a test to the main run is wired through suite → campaign → cycle.                                                                               |

### 3. SUT artifacts

| Artifact                                              | What it is                                                                      | How to use                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `https://github.com/katalon-studio/katalon-demo-cura` | CURA's PHP source (public). Authoritative for _what the code says_.             | Read when a server-side claim is load-bearing (CSRF, session, redirects, validation). `gh api repos/katalon-studio/katalon-demo-cura/contents/<file>.php --jq '.content' \| base64 -d`. **Note:** the deployed app drifts from the source (`IDENTIFIED_GAPS.md` §G-SEC-1). Trust live observation over source when they disagree. |
| `https://katalon-demo-cura.herokuapp.com/`            | The deployed app. Authoritative for _what users actually experience_.           | Read when authoring needs the rendered HTML, the visible text, the actual element layout. Open it. Run probes against it. The suite tests _this_, not the github source.                                                                                                                                                          |
| `.venv/lib/python3.14/site-packages/ocarina/`         | Ocarina framework source (in the venv). Strictly typed, exhaustively annotated. | Read to confirm a public type / kwarg / signature. The skill `review-type-ignore` flags `type: ignore` on this surface as highest-suspicion.                                                                                                                                                                                      |

### 4. Project conventions

| Artifact                         | What it is                                                                                                      | How to use                                                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `CLAUDE.md`                      | Contributor context: rules, conventions, architecture, the Layout block, the hard-won rules.                    | The first read for any new contributor or any non-trivial change. Many of the skills cross-reference specific rule sections. |
| `README.md`                      | Human-facing entry point: what the project is, what makes it different, how to read the results, how to run it. | Onboarding handoff to anyone who isn't a contributor (a reviewer, a manager, a third party).                                 |
| `<project-root>/CLAUDE.local.md` | Gitignored, machine-specific paths (chromedriver, ocarina source clones).                                       | Local-machine config; not portable. Each contributor maintains their own.                                                    |

### 5. Constants and configs

| Artifact                            | What it is                                                                | How to use                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `src/constants/urls.py`             | Canonical full URLs for every CURA page reachable from the suite.         | Use these in POMs and probes (never inline a URL elsewhere — `CLAUDE.md` rule).                                  |
| `src/constants/credentials.py`      | `DEMO_USERNAME` / `DEMO_PASSWORD` (public, hardcoded).                    | Use the constants by name; never retype the literal (`CLAUDE.md` → "Use the constant — never retype its value"). |
| `src/constants/transient_errors.py` | Exception types that trigger auto-retry.                                  | Read before adding a new entry — deterministic findings never land here.                                         |
| `<project-root>/pyproject.toml`     | Project metadata, ruff config, mypy config, dependencies.                 | Source of: the strictness contract (`ruff select = ["ALL"]`, strict mypy). New code respects it.                 |
| `.github/workflows/ci.yml`          | PR-gating workflow — lint + typecheck.                                    | Read to know what gates merges.                                                                                  |
| `.github/workflows/e2e.yml`         | Manual e2e dispatch — full matrix on Firefox + Chrome with `--workers 3`. | Read the matrix and the timeout setting (`WAIT_TIMEOUT: 15`).                                                    |

### 6. Run history (the empirical layer)

| Artifact                                          | What it is                                                                                                    | How to use                                                                                      |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `<project-root>/.reports/json/*.json`             | Machine-readable per-run results (nested by campaign / suite / test). One file per run, random UUID filename. | Pick by mtime (see `pick-reports`). Feed to `review-suite-stability` for cross-replay analysis. |
| `<project-root>/.reports/docx/<run-id>/**/*.docx` | DOCX proofs — one per test, embedding the screenshot sequence.                                                | Pick by run-id (see `pick-reports`). Open for visual journey verification.                      |
| `<project-root>/.ocarina_logs_<id>/**/*.log`      | Per-test chronological logs with success / failure markers, screenshot citations, tracebacks.                 | Pick by mtime (see `pick-logs`). The textual companion to the DOCX.                             |
| `<project-root>/.screenshots/*.png`               | Raw screenshots, PASS (`PASS_<uuid>.png`) or FAIL bursts (`FAIL_<uuid>_<n>.png`).                             | Pick by mtime (see `pick-screenshots`). The raw frames.                                         |
| GA workflow runs (`gh run list`)                  | Cloud history of the manual e2e dispatch.                                                                     | The canonical reference. `gh run view <id> --log` returns the full trace.                       |

### 7. External / user-facing resources

This category is per-project; for CURA specifically it's mostly empty (CURA is a demo, no user manual). For a real product, fill in:

| Artifact (when applicable)     | What it is                                      | How to use                                                                                                                  |
| ------------------------------ | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| User manual / help docs        | The system's official user-facing instructions. | Source of expected workflows, expected outputs, terminology — the **user's** model.                                         |
| API docs                       | Public endpoint contracts.                      | Source of expected request/response shapes for any direct-HTTP work (out of scope here per CLAUDE.md, but the slot exists). |
| Product spec / PRD             | The business-side requirements document.        | Source of expected business rules and acceptance criteria, complementary to the FRD.                                        |
| Design system / Figma          | The visual contract.                            | Source of expected layouts, copy, button labels — useful for cross-checking selector locators against intent.               |
| Support tickets / bug reports  | Real user-observed defects.                     | Source of edge cases and adjacent scenarios (feeds `extend-coverage`).                                                      |
| Analytics / session recordings | Real user behaviour data.                       | Source of which flows are actually used — guides test prioritisation.                                                       |

For CURA-as-SUT, none of these exist. State that explicitly in the report — "user manual: not applicable for CURA (demo)" rather than omitting.

## Procedure

### 1. Walk the seven categories in order

Inventory by directory listing, file read, and (for SUT-source / GA) external query.

```bash
# specs
ls CURA_FRD.md CURA_TEST_STRATEGY.md IDENTIFIED_GAPS.md

# test code surfaces
find src/pages -name "*.py" -not -name "__init__.py"
find src/lib/connectors/test_steps -name "*.py" -not -name "__init__.py"
find src/tests/scenarios -name "*.py" -not -name "__init__.py"
find src/tests/suites src/tests/campaigns src/tests/cycles -name "*.py" -not -name "__init__.py"

# constants
ls src/constants/*.py

# run history (latest only, by mtime)
ls -t <project-root>/.reports/json/*.json 2>/dev/null | head -3
ls -dt <project-root>/.reports/docx/*/ 2>/dev/null | head -3
ls -dt <project-root>/.ocarina_logs_* 2>/dev/null | head -3
```

For SUT artifacts: don't dump the GitHub source — note the repo URL and the `gh api` snippet. Don't open the live deployment in this skill; the
snapshot is what's _available_, not what's _currently rendered_.

### 2. Per artifact, capture (in one or two lines)

- Path / URL.
- What it contains (one short summary).
- How it feeds the authoring loop (one short sentence).

Do not paraphrase the artifact's contents at length — the catalog points; the reader opens.

### 3. Flag missing slots

For category 7 (external / user-facing), explicitly list which slots **don't exist for this project** rather than omitting them. "User manual: not
applicable (CURA is a demo)" is information.

For any other category where a _normally-present_ artifact is absent — e.g. no `IDENTIFIED_GAPS.md` (would be unusual here), no `CURA_FRD.md` (would
block test authoring) — surface as a **structural gap**.

### 4. Surface — produce the catalog

Use this exact template:

```markdown
# Test-base assessment — <target> (<date>)

## 1. Specs

<one row per artifact: path, what, how to use>

## 2. Existing test code

<rows; group POMs / connectors / scenarios / suite tree>

## 3. SUT artifacts

<rows>

## 4. Project conventions

<rows>

## 5. Constants and configs

<rows>

## 6. Run history

<rows>

## 7. External / user-facing resources

<rows; explicitly mark "not applicable" slots>

## Structural gaps (if any)

- <slot that should exist but doesn't, with one-line rationale>

## Summary

- Specs: N artifacts.
- Test code: K POMs / L connectors / M scenarios / S suites / C campaigns / 1 cycle.
- SUT: live deployment + github source + Ocarina venv.
- Run history (latest): JSON `<file>`, DOCX `<run-id>`, logs `<root>`, screenshots dir.
- External resources: <list of "not applicable" slots, or the populated ones>.
- Structural gaps: <count, or "(none)">.
```

Print the catalog. Default: in chat. If the user wants it persisted, save it to a place they pick — this skill does not write to a default location.

### 5. Stop. The user reads.

The catalog is the deliverable. Decisions about what to read deeper, what to extend, what to author come from the user (and feed into
`extend-coverage`, `manage-backlog`, `empiricism`).

## When to run this skill

- The user asks: "what do we have?", "inventory the test base", "what can I work from?", "onboard me", "release-readiness survey".
- Before invoking `extend-coverage` — knowing what's _already_ a fact lets you find what's missing more efficiently.
- Before invoking `manage-backlog` Mode A (generate) — the catalog points at sources to scan for follow-ups.
- When onboarding a new contributor.
- When preparing a release-candidate review.

## What this skill does NOT do

- It does not audit or grade. Reading the test code looking for bugs is the `review-*` family's job; this skill catalogues _what's there_, not how
  good it is.
- It does not invent missing artifacts. If a user manual doesn't exist, the catalog says so; it does not write one.
- It does not deep-paraphrase artifacts. The catalog points; the reader opens.
- It does not list every per-file fact (every selector, every connector signature). The granularity is "what's in this file / directory / source";
  deeper reads are follow-up motions.
- It does not produce metrics or counts that don't matter — "N tests pass" is meaningless per `CURA_TEST_STRATEGY.md` §7 ("don't track a total").
  Per-category counts where they help (POM count, scenario count) are fine.
