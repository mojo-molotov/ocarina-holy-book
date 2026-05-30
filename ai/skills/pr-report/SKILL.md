---
name: pr-report
description: Write the PR description for the current branch, picking the right *shape* of report for the PR. The discipline: a refactoring PR gets a **refactoring report** (what was reshaped, what stayed the same, net delta, risk surface, minimal test plan) — not the test-strategy template (hierarchy slice, suite/campaign tree, expected pass/fail) that's appropriate when test boundaries shift. Use whenever the user asks to write a PR description, draft a PR body, summarise a branch for review, prepare a release-candidate PR, or run `gh pr create`. Detect the PR type before reaching for a template; if the diff doesn't add/remove/relocate any test, it's a refactor — the report frames the *reshape*, not the *test plan*.
---

# Write a PR report — the right shape for the PR

The project's `CLAUDE.md` ships a default PR-description shape that leans heavily on test strategy — `## Summary` + `## Test plan` + a _hierarchy
slice_ when the cycle/campaign/suite/test tree shifts. That shape is right when the PR moves test boundaries. When the PR is a **refactor** — internal
reshape, type hygiene, consolidation, dead-code removal, a discipline applied uniformly to existing tests — the report should frame the _refactor_,
not the test plan. A long Test plan and a hierarchy slice on a refactor PR are noise; they push the actual change out of view.

This skill: detect the PR type and pick the right template. (Dead-code-removal PRs are the typical output of `review-dead-code`; the report template
below covers them under the refactor shape.)

## Detect the PR type

Run these against the branch (assume `main` is the base, override as needed):

```bash
# 1. What changed at all?
git diff --stat main..HEAD

# 2. Did any test get added / removed / renamed / moved? (The hard signal of a test-strategy PR.)
git diff --name-status main..HEAD -- 'src/tests/scenarios/**' 'src/tests/suites/**' 'src/tests/campaigns/**' 'src/tests/cycles/**'
git diff main..HEAD -- 'src/tests/scenarios/**' | grep -E "^[+-].*create_(selenium|playwright)_test\(name="

# 3. Was a suite / campaign / cycle wired differently? (Same hard signal.)
git diff main..HEAD -- 'src/tests/suites/**' 'src/tests/campaigns/**' 'src/tests/cycles/**'

# 4. Doc-only?
git diff --name-only main..HEAD | grep -v '\.py$' | wc -l
git diff --name-only main..HEAD | grep '\.py$' | wc -l

# 5. Bug fix sized?
git diff --stat main..HEAD | tail -1   # one or two files, small delta → likely fix
```

Decision tree:

| Signals                                                                                                                                                                                               | PR type           | Template                                                                                             |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------------------- |
| New / deleted / renamed scenario; added/removed `create_*_test(name=` (selenium/playwright); suite/campaign membership changed                                                                        | **Test-strategy** | The existing `CLAUDE.md` "PR descriptions" section — `## Summary` + `## Test plan` + hierarchy slice |
| None of the above; changes concentrate in `src/pages/`, `src/lib/`, `src/constants/`, or scenario _internals_ (screenshots, dispatcher additions, type fixes, mechanical renames) with no flow-change | **Refactor**      | The refactor template below                                                                          |
| Small targeted diff fixing a specific defect; failing test or bug reference; no test-shape change                                                                                                     | **Bug fix**       | The bug-fix template below                                                                           |
| Only `.md` files changed                                                                                                                                                                              | **Doc-only**      | The doc-only template below                                                                          |
| Two patterns at once (the common case is _refactor + the test that proves it_)                                                                                                                        | **Mixed**         | Lead with the dominant frame (usually refactor); fold the other into a sub-section                   |

Tricky case: a PR that edits _many_ scenario files but doesn't add/remove tests (e.g. the screenshots-per-`drive_page` rollout). Those scenarios
changed, but the _test shape_ didn't — it's a refactor, not a test-strategy PR. Frame as refactor.

## Refactor template (the one the user is reminding you to use)

```markdown
## Summary

<one short paragraph: the rule / pattern applied + the unit of change. Lead with the _reshape_, not the file list.>

## What changed

- <reshape 1 — moved X → Y, consolidated A+B into C, replaced N call sites of D with E, removed dead F, added dispatcher G…>
- <reshape 2>
- <reshape 3>

(Verb-led bullets. Concrete. No "improved" or "cleaned up" without saying what.)

## What stayed the same

<the contract — the _interface_ / _behaviour_ the refactor did NOT touch. Important on a refactor: tells the reader what is and isn't risk. Examples:
"test names unchanged", "no scenario was added, removed, or renamed", "POM public methods unchanged", "CLI flags unchanged".>

## Net delta

`Net: +N / −M lines, K fewer files` (or "K new files"). Add concrete numerics where they matter: type:ignores removed, lines of dead code dropped,
dispatcher paths added, screenshots-per-drive_page now true everywhere, etc.

## Risk surface

<one short paragraph: where this could regress, and what specifically proves it didn't. Don't write a test plan, write a _risk statement_ and the one
or two checks that close it.>

## Test plan

- [x] `ruff format && ruff check && mypy` — clean
- [x] Full e2e cycle on both browsers — <Firefox: …; Chrome: …>
- [ ] Manual the e2e workflow workflow run on the branch (if the change is matrix-sensitive)

(No hierarchy slice — test boundaries unchanged. If you find yourself drafting one, the PR is not a pure refactor; re-detect.)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Test-strategy template

Use the existing PR-descriptions section in `CLAUDE.md`. Key obligations: `## Summary` leading with the rule/pattern; `## Test plan` checklist with
the explicit local result `All N tests pass locally (X.Xs)`; hierarchy slice rendered when the cycle/campaign/suite/test tree shifts. Optional
sub-sections (Filesystem, CLAUDE.md, Net delta) when they earn space.

## Bug-fix template

```markdown
## Summary

<one paragraph: what was broken, the root cause (from the actual evidence — probe output, log, PHP, etc.), the fix in one sentence.>

## Evidence

<the failing-then-passing artifact: probe result, log excerpt, the assertion message before and after, the screenshot diff if visual.>

## Test plan

- [x] `ruff format && ruff check && mypy` — clean
- [x] Full e2e cycle on both browsers — <result>
- [ ] Manual the e2e workflow workflow (if matrix-sensitive)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Doc-only template

```markdown
## Summary

<one paragraph: what conventions / docs changed and why.>

## Sections touched

- `<doc>`: <section> — <one-line on the change>
- `<doc>`: <section> — <one-line>

(No test plan section. Lint / typecheck don't run on doc-only changes; the existing CI gate handles that.)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Procedure

1. **Run the detection commands above** and decide the PR type. If unsure, ask the user — better than guessing wrong and writing the wrong template.
2. **Pick the template.** Refactor PRs get the refactor template, full stop — even if there is a _companion_ test landing in the same PR, the refactor
   frames the PR.
3. **Fill it.** Concrete, verb-led, lead with the rule/pattern. Cite the local test result verbatim. Cite net delta with numbers.
4. **Render the title.** Keep it short (≤ 70 characters), conventional-commit-flavoured (`refactor:`, `test:`, `fix:`, `docs:`), match the dominant
   frame.
5. **Confirm before pushing the PR.** Print the draft. Wait for the user's go. Do not run `gh pr create` until they say so.

## Examples

### Refactor (use the refactor template)

A PR that applies the "every `drive_page` produces a screenshot" rule across all existing scenarios. No test added, removed, or renamed; the test
_shape_ is identical. The PR is a refactor.

Wrong frame: "## Test plan: 31 tests pass locally" + hierarchy slice. Right frame: "**What changed**: 12 scenario files gained `log_and_screenshot`
calls on the act that captures each `drive_page`'s resulting page. **What stayed the same**: every test name, every assertion. **Net delta**: +N
screenshots per test, identical pass/fail."

### Test-strategy (use the test-strategy template)

A PR that splits one back-button test into two — server-side invalidation + BFcache exposure. New tests added; the suite tree shifted. Hierarchy slice
and test plan are exactly what a reviewer needs.

### Mixed — refactor + the test that proves it (lead with refactor)

A PR introducing `pages/components/sidebar.py` (refactor) plus a new `sidebar_navigation.py` test (test-strategy). Lead with the component refactor in
`## Summary`, list the new test under `## What changed`, mention the test in `## Test plan`. A small hierarchy-slice insert under `## What changed` is
fine — but don't make the whole PR look like a test-strategy PR; the dominant change is the refactor.

## When to run this skill

- The user asks: "write a PR for this", "draft the PR body", "summarise the branch", "what should the PR description say", "run `gh pr create`".
- Before pushing a PR.
- When reviewing the user's draft PR description and the framing looks wrong (e.g. a refactor with a 30-line test plan).

## What this skill does NOT do

- It does not run `gh pr create` without the user's go-ahead — drafts only.
- It does not pick a hybrid template. Pick one frame and stick to it; folding two templates produces a long, unfocused report.
- It does not invent test results. If you didn't run the suite, say so — `[ ] full e2e cycle pending` is honest. A faked `[x]` is the kind of thing
  the rest of CLAUDE.md exists to prevent.
