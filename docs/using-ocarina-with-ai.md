---
sticky: 1
description: Hello it's me, your new best friend!

date: 2026-05-16

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-playing-ocarina.png
---

# Using Ocarina with AI

A working setup: a full test cycle built alongside Claude Code and Ocarina, against the public Katalon CURA demo.

[📖 Get the AI example as a reference.](https://github.com/mojo-molotov/ocarina-with-ai-example)

## The three spiritual stones

1. `CLAUDE.md` at the project root.
2. `skills/` with one `<name>/SKILL.md` per procedure.
3. Verification rule: every SUT claim comes from observation (probe, `gh api`, `curl -v`), never inference.

## `CLAUDE.md`

Two variants. `CLAUDE.md` is full (rules + project layout, hierarchy, conventions, CI shape, PR template). `CLAUDE.slim.md` is rules only. Slim when
context is heavy; full for onboarding and reviews. Full wins on disagreement.

Onboarding steps (venv, `pip install`, the skill battery copied into Claude Code, `ruff` /&nbsp;`mypy` /&nbsp;`pre-commit`, runner smoke-check) live
in `setup-environment`.

Rules:

**Security testing is functional and static, never active.** No payloads, no crafted requests, no DevTools DOM manipulation. Black-hat scenarios go
through the normal UI.

**Use constants.** Named values aren't inlined.

**Datasets are human decisions.** Proposing doesn't run.

**Verify SUT behavior empirically.** Probe, `gh api`, or `curl -v`. Never inference. Re-derive each time: a probe answers only for what it ran; a
prior diagnosis only for that run.

Each rule carries a one-line "_why_."

## `skills/`

One Markdown file per skill, YAML frontmatter + body. Ten families.

### Review (14)

Static reads; surface findings.

- `review-spec-gaps&nbsp;—&nbsp;clarification questions on the FRD.
- `review-watcher-misuse`&nbsp;—&nbsp;`watcher.report(...)` against the negative-only convention.
- `review-compartmentalisation-leaks`&nbsp;—&nbsp;URLs, selectors, magic numbers out of place.
- `review-dead-code`&nbsp;—&nbsp;unused connectors /&nbsp;POMs /&nbsp;scenarios /&nbsp;suites /&nbsp;fragments /&nbsp;constants; per finding: delete,
  incubate (`<source-root>/incubator/`, dependency tree preserved), or keep.
- `review-hierarchy-naming`&nbsp;—&nbsp;parent ⊃ same-name child in the cycle tree (most often `Campaign("X") ⊃ Suite("X")`); rename the child for its
  actual segment scope (the hierarchy is strict — no collapsing).
- `review-report`&nbsp;—&nbsp;classify each FAIL&nbsp;/&nbsp;SKIP for one run.
- Plus: `review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers`, `review-comment-drift`,
  `review-suite-stability`, `review-intent-collisions`, `review-watcher-emissions`.

### Analyse (4)

- `analyse-flakiness`&nbsp;—&nbsp;widen the transient-error net; chronic deaths are real flakes.
- `analyse-fixture-flakiness`&nbsp;—&nbsp;instrument setup/teardown; surface cross-test contamination.
- `analyse-watcher-flakiness`&nbsp;—&nbsp;with/without each watcher, interval sweep.
- `analyse-screenshot-flakiness`&nbsp;—&nbsp;group by `(test, step, browser)`, spot differences.

### Black-hat (6)

- `business-attack-ideation`&nbsp;—&nbsp;bring the product down.
- `incoherence-attack-ideation`&nbsp;—&nbsp;each step legal, the set impossible.
- `persistence-attack-ideation`&nbsp;—&nbsp;repeated retries on blocked actions.
- `permission-appropriateness-audit`&nbsp;—&nbsp;is the access model itself appropriate?
- `bfcache-exposure-ideation`&nbsp;—&nbsp;BFCache attacks.
- `lateral-resource-ideation`&nbsp;—&nbsp;IDOR via the address bar only.

### Comprehend (4)

- `assess-test-base`&nbsp;—&nbsp;catalog the suite.
- `assess-ecosystem`&nbsp;—&nbsp;bounded public research, token-budget capped.
- `understand-sut-constraints`&nbsp;—&nbsp;SUT bounds that break parallel tests.
- `understand-ocarina`&nbsp;—&nbsp;walk the docs.

### Pick (3)

By mtime, never filename.

- `pick-screenshots`, `pick-logs`, `pick-reports`.

### Author (9)

Each produces a deliverable.

- `empiricism`&nbsp;—&nbsp;verify before encoding; don't overwrite intentional-fail gap tests.
- `write-a-probe`&nbsp;—&nbsp;throwaway script, gitignored.
- `write-test-strategy`&nbsp;—&nbsp;generate the test-strategy doc from the suite (scope, types, coverage tables, cycle tree, pass/fail, gaps, CI
  matrix).
- `plan-test-effort`&nbsp;—&nbsp;first-pass, naïve effort plan; criticality (critical/major/minor), lightweight risk register,
  S&nbsp;/&nbsp;M&nbsp;/&nbsp;L weights, open questions for the deeper pass.
- `extend-coverage`&nbsp;—&nbsp;extend coverage from existing assets.
- `update-frd-and-tests`&nbsp;—&nbsp;propagate a spec update in the project-internal FRD; upstream systems (Confluence, Jira, …) stay read-only.
- `manual-reproduction-guide`&nbsp;—&nbsp;human-runnable repro.
- `manage-backlog`&nbsp;—&nbsp;`BACKLOG.md`.
- `pr-report`&nbsp;—&nbsp;PR-type-aware report.

### Refactor (2)

- `refactor-fragmentation`&nbsp;—&nbsp;DRY per user preference.
- `introduce-pom-retries`&nbsp;—&nbsp;POM-internal retries with the two-test split (first-try + with-retries).

### State (1)

- `question-state`&nbsp;—&nbsp;interrogate the environment before trusting a result.

### Setup (1)

- `setup-environment`&nbsp;—&nbsp;venv, dev tooling, the Ocarina skill battery copied into Claude Code's skills directory, driver paths in
  `CLAUDE.local.md`, pre-commit loop, runner smoke-check.

### Run (1)

- `propose-visual-review`&nbsp;—&nbsp;before a local dispatch, offer `--not-headless` (watch the browser play out) vs headless (CI-shaped). Composes
  the command; user runs.

## Recurring chains

**Suite isn't green:** `review-report`&nbsp;→&nbsp;`analyse-*` →&nbsp;`write-a-probe` →&nbsp;finding lands in `IDENTIFIED_GAPS.md` /&nbsp;FRD
/&nbsp;scenario comment &nbsp;→&nbsp;probe deleted.

**Black-hat scenario looks promising:** `empiricism` →&nbsp;`extend-coverage` (often intentional-fail).

**Spec changes:** `update-frd-and-tests` (FRD first, tests follow). Gap tests are reframed, not flipped.

**New Ocarina primitive needed:** `understand-ocarina` first, then writing.

**About to dispatch a run:** `propose-visual-review`&nbsp;—&nbsp;headed (`--not-headless`) or headless (CI-shaped)? Composes the command; user runs.

## Discipline

**Surface, don't apply.** Skills produce; the user decides.

**Empirical, not assertive.** Every SUT claim is observed, cited, dated. Ritual phrase: _"Fair point, I'm assuming. Let me verify empirically."_

**Gap tests are reframed, not turned green.** Invert the assertion, rename, move the strategy-doc row, log the resolution in `IDENTIFIED_GAPS.md`. One
motion via `update-frd-and-tests`.

**Watcher emissions are negative signals only.** A watcher emitting _"login succeeded"_ breaks the contract.

**Distributed when scarcity is shared.** If workers contend on a SUT-capped resource (sessions, slots, quotas), coordinate through distributed
primitives. Otherwise a worker-local in-memory cache is fine&nbsp;—&nbsp;provided keys can't collide and generation is thread-safe.

**Mtime, not filename.** UUID suffixes are random; `pick-*` sorts by mtime.

## What this setup isn't

- Doesn't generate tests autonomously.
- Doesn't patch hallucinations in CI; a failure triggers `review-report` + `analyse-*`.
- Doesn't rewrite the spec; only `update-frd-and-tests` does, with a revision line.
- Doesn't run active security tests. Ever.

## Exposed resources

- https://mojo-molotov.github.io/ocarina-holy-book/llms.txt
- https://mojo-molotov.github.io/ocarina-holy-book/llms-full.txt
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.md
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.slim.md
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-ru.pdf
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-en.pdf
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-fr.pdf

<llm-exclude>

---

![Mojo playing ocarina](/assets/content/docs/creatives/mojo-playing-ocarina.png)

<p align="center" class="good-work-mojo-msg"><i>Oh wow!<br/>You tweaked it a lot, Mojo reader.</i></p>

---

<p align="center" class="inspiring-quote">"On Earth and Space, he has all the tricks."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;▒▒█𝚃𝙾𝙿 𝚂𝙴𝙲𝚁█𝚃 //&nbsp;𝚂𝙲𝙸 //&nbsp;𝙽▒▒▒▒𝙾𝙵𝙾𝚁𝙽</p>

</llm-exclude>
