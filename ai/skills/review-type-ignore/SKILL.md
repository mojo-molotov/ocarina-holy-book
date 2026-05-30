---
name: review-type-ignore
description: Audit a Python source tree (or diff / branch / file list) for `# type: ignore` comments that suppress mypy errors, with extra suspicion for ignores that suppress errors on Ocarina framework built-ins (`drive_page`, `act`, `create_selenium_test`, `Scenario`, `TestSuite`, `TestCampaign`, `TestCycle`, `POMBase`, `WebDriversPool`, `DriverBuilder`, `bootstrap`, `ILogger`, `Effect`, …). Use whenever the user asks to audit type suppressions, review `type:ignore` usage, vet a PR for hidden type errors, check for sketchy type-checker bypasses, or harden a release. Use defensively after any refactor that touched Ocarina wiring — that is when these suppressions tend to creep in. Surface findings; never silently remove a suppression.
---

# Review — `# type: ignore` audit

Audits a Python source tree (or a diff / branch / file list) for `# type: ignore` comments and reports which ones are suspicious. Highest suspicion:
ignores on lines that reference Ocarina framework built-ins. Ocarina is strictly typed and exhaustively annotated; a `type: ignore` on its surface
almost always papers over a real authoring mistake (wrong import, wrong kwarg, drifted custom-type annotation), and the right fix is to correct the
type, not silence the checker.

Default target: `src/`. For a different target, ask the user.

The audit surfaces findings only. **It never edits a `type: ignore` automatically.** A suppression is sometimes the right call (genuinely unfixable
framework wart, mypy-version regression, intentional gradual-typing escape hatch). The job here is to make those decisions visible, not to remove them
silently.

## Procedure

### 1. Locate every `# type: ignore` in the target

```bash
grep -rnE "type:\s*ignore" <target> --include="*.py"
```

For a diff/branch audit, restrict to changed Python files:

```bash
git diff --name-only main..HEAD -- '*.py' | xargs grep -nE "type:\s*ignore" 2>/dev/null
```

### 2. Classify each hit

| Tier         | Trigger                                                      | Why                                                                                                                                                                |
| ------------ | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **High**     | line references any symbol from the Ocarina list (see below) | Ocarina is strictly typed; a suppression here almost always hides a real misuse — wrong import, wrong kwarg, drifted `Effect` / `Callable[[POM], POM]` annotation. |
| **Moderate** | bare `# type: ignore` (no error code)                        | Suppresses every error on the line, including future ones. A coded form (`# type: ignore[name-defined]`) is the honest minimum.                                    |
| **Low**      | coded `# type: ignore[<code>]` not touching Ocarina          | Surface for review anyway: the suppression may be stale, or the underlying cause may now be fixable.                                                               |
| **Stale**    | `mypy --warn-unused-ignores` flags it                        | The underlying error no longer exists; remove the ignore.                                                                                                          |

### 3. Diagnose each finding

For each hit, find out **what error the ignore is hiding** before recommending. Two ways:

- **Cheap, batch:** `mypy --warn-unused-ignores src/` flags every stale suppression in one pass. Start here.
- **Per-finding, when stale didn't catch it:** the surest way is to remove the ignore in a throwaway working copy and re-run mypy. Do this in a
  probe-style scratch (a copy of the file, or `git stash` after a local edit) — **never directly in the source tree** when running the audit on
  someone else's branch.

If a diagnosis isn't possible in the audit context (e.g. read-only review), record the line content + tier and flag for follow-up.

### 4. Report

Use this exact template:

```markdown
# `type: ignore` audit — <target>

## High — Ocarina symbol on the suppressed line

- <path>:<line> — `<line content>`
  - Suppressed error (with the ignore removed): `<mypy message, or "not verified — read-only audit">`
  - Likely cause: <one-line diagnosis>
  - Recommendation: <fix the type / replace bare ignore with `# type: ignore[<code>]` + `# why: …` / remove if stale>

## Moderate — bare `# type: ignore`

- <same shape>

## Low — coded `# type: ignore[<code>]`

- <same shape>

## Stale — `mypy --warn-unused-ignores`

- <path>:<line> — underlying error gone, remove the ignore.

## Summary

- High: N | Moderate: N | Low: N | Stale: N
- Verdict: <ship it | block, fix the High items first>
```

Print the report; do not write it to a file unless the user asks.

### 5. Stop. The user decides.

Do not edit. Do not auto-remove. Do not propose a sweeping clean-up commit. Hand the report over and wait.

## Ocarina symbols — the "High" trigger list

Any `# type: ignore` on a line that references one of these is **High**. Match by substring (a tokenised match is more precise but substring is good
enough as a first pass; the false-positive cost is one line of review).

| Category       | Symbols                                                                                                                                                                                                                 |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DSL            | `drive_page`, `act`, `Scenario`, `ChainRunner`                                                                                                                                                                          |
| Test hierarchy | `create_selenium_test` / `create_playwright_test`, `create_playwright_watcher`, `TestSuite`, `TestCampaign`, `TestCycle`, `has_test_cycle_failed`                                                                       |
| Driver / pool  | `create_selenium_driver`, `create_selenium_drivers_pool`, `create_playwright_drivers_pool`, `PlaywrightDriver`, `WebDriversPool`, `SeleniumWebDriversPool`, `DriverBuilder`, `BuiltSeleniumWebDriver`, `BuiltWebDriver` |
| POM base       | `POMBase`, `SeleniumTitleMixin`, `SeleniumBackAndForwardNavigationMixin`, `PlaywrightTitleMixin`                                                                                                                        |
| CLI / launcher | `SeleniumCliStoreSingleton` / `PlaywrightCliStoreSingleton`, `create_selenium_auto_cli_store` / `create_playwright_auto_cli_store`, `bootstrap`, `run_plugins`                                                          |
| Types          | `ILogger`, `Effect`, `Thunk`, `SupportedSeleniumBrowser`, `SupportedLogger`, `TestName`, `TestScenario`, `TestScenarioFragment`, `SeleniumTestScenario` / `PlaywrightTestScenario`, `TestCycleResults`                  |
| Reports        | `pretty_print_results`, `generate_docx_proof`, `generate_json_results`, `timing`                                                                                                                                        |

If the project adopts a new Ocarina symbol that becomes commonly used here, add it. Treat additions as a dataset change — surface the proposed
addition to the user before editing this list (see `CLAUDE.md` → "Datasets are authoring decisions").

## Why Ocarina symbols are the highest tier

Ocarina is exhaustively annotated; you can confirm any signature in `.venv/lib/python3.14/site-packages/ocarina/`. When mypy complains on
`drive_page(...)`, an `act(...)` chain, a `create_selenium_test(name=…, …)`, or a custom-typed `Effect` / `Callable[[POM], POM]`, the cause is almost
always one of:

- **Wrong import** — runtime symbol where a `TYPE_CHECKING` import is expected, or vice versa.
- **Wrong kwarg or arg shape** — `max_size` vs `workers`, missing keyword-only argument, swapping a `Sequence[Case]` for a `list[Case]`.
- **Drifted custom-type annotation** — an `Effect` / `Callable[[POM], POM]` whose signature no longer matches the connector it wraps.

In every one of those, the correct response is to fix the type. A `# type: ignore` here reads as _"I gave up and shipped the misuse"_ — exactly what
this audit exists to surface.

## When to run this skill

- The user asks: "audit type:ignore", "review type suppressions", "any sketchy `# type: ignore` in this branch?", "vet this PR".
- A PR review touches Ocarina wiring (factory builders, fragments, connector signatures, custom-type aliases).
- Preparing a release / hardening pass.
- Defensively after a refactor — refactors are when these suppressions creep in.

You may run it without prompting if you see a new `# type: ignore` being added in a diff you're already reviewing.

## What this skill does NOT do

- It does not edit source files.
- It does not remove suppressions, even stale ones — those go in the **Stale** section of the report, recommendation for the user.
- It does not run the full lint/typecheck pipeline; it is one focused audit. If the user wants a fuller review, run it alongside the project's
  existing `ruff format && ruff check && mypy` and pre-existing review skills.
