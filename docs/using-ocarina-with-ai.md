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

## `CLAUDE.md` (and `CLAUDE.slim.md`)

Two variants. `CLAUDE.md` is full (rules + project layout, hierarchy, conventions, CI shape, PR template). `CLAUDE.slim.md` is rules only. Slim when
context is heavy; full for onboarding and reviews. Full wins on disagreement.

Onboarding steps (venv, `pip install`, `ruff` / `mypy` / `pre-commit`, runner smoke-check) live in `setup-environment`.

Rules:

**Security testing is functional and static, never active.** No payloads, no crafted requests, no DevTools DOM manipulation. Black-hat scenarios go
through the normal UI.

**Use constants.** Named values aren't inlined.

**Datasets are human decisions.** Proposing doesn't run.

**Verify SUT behaviour empirically.** Probe, `gh api`, or `curl -v`. Never inference. Re-derive each time: a probe answers only for what it ran; a
prior diagnosis only for that run.

Each rule carries a one-line "_why_."

## `skills/`

One Markdown file per skill, YAML frontmatter + body. Nine families.

### Review (12)

Static reads; surface findings.

- `review-spec-gaps` — clarification questions on the FRD.
- `review-watcher-misuse` — `watcher.report(...)` against the negative-only convention.
- `review-compartmentalisation-leaks` — URLs, selectors, magic numbers out of place.
- `review-report` — classify each FAIL / SKIP for one run.
- Plus: `review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers`, `review-comment-drift`,
  `review-suite-stability`, `review-intent-collisions`, `review-watcher-emissions`.

### Analyse (4)

- `analyse-flakiness` — widen the transient-error net; chronic deaths are real flakes.
- `analyse-fixture-flakiness` — instrument setup/teardown; surface cross-test contamination.
- `analyse-watcher-flakiness` — with/without each watcher, interval sweep.
- `analyse-screenshot-flakiness` — group by `(test, step, browser)`, spot differences.

### Black-hat (6)

- `business-attack-ideation` — bring the product down.
- `incoherence-attack-ideation` — each step legal, the set impossible.
- `persistence-attack-ideation` — repeated retries on blocked actions.
- `permission-appropriateness-audit` — is the access model itself appropriate?
- `bfcache-exposure-ideation` — BFCache attacks.
- `lateral-resource-ideation` — IDOR via the address bar only.

### Comprehend (4)

- `assess-test-base` — catalogue the suite.
- `assess-ecosystem` — bounded public research, token-budget capped.
- `understand-sut-constraints` — SUT bounds that break parallel tests.
- `understand-ocarina` — walk the docs.

### Pick (3)

By mtime, never filename.

- `pick-screenshots`, `pick-logs`, `pick-reports`.

### Author (7)

Each produces a deliverable.

- `empiricism` — verify before encoding; don't overwrite intentional-fail gap tests.
- `write-a-probe` — throwaway script, gitignored.
- `extend-coverage` — extend coverage from existing assets.
- `update-frd-and-tests` — propagate a spec update.
- `manual-reproduction-guide` — human-runnable repro.
- `manage-backlog` — `BACKLOG.md`.
- `pr-report` — PR-type-aware report.

### Refactor (2)

- `refactor-fragmentation` — DRY per user preference.
- `introduce-pom-retries` — POM-internal retries with the two-test split (first-try + with-retries).

### State (1)

- `question-state` — interrogate the environment before trusting a result.

### Setup (1)

- `setup-environment` — venv, dev tooling, driver paths in `CLAUDE.local.md`, pre-commit loop, runner smoke-check.

## Recurring chains

**Suite isn't green:** `review-report` → `analyse-*` → `write-a-probe` → finding lands in `IDENTIFIED_GAPS.md` / FRD / scenario comment → probe
deleted.

**Black-hat scenario looks promising:** `empiricism` → `extend-coverage` (often intentional-fail).

**Spec changes:** `update-frd-and-tests` (FRD first, tests follow). Gap tests are reframed, not flipped.

**New Ocarina primitive needed:** `understand-ocarina` first, then writing.

## Discipline

**Surface, don't apply.** Skills produce; the user decides.

**Empirical, not assertive.** Every SUT claim is observed, cited, dated. Ritual phrase: _"Fair point, I'm assuming. Let me verify empirically."_

**Gap tests are reframed, not turned green.** Invert the assertion, rename, move the strategy-doc row, log the resolution in `IDENTIFIED_GAPS.md`. One
motion via `update-frd-and-tests`.

**Watcher emissions are negative signals only.** A watcher emitting _"login succeeded"_ breaks the contract.

**Horizontal scaling first.** No in-memory state at the worker level. Distributed primitives only.

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
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-en.pdf
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-fr.pdf

<llm-exclude>

---

![Mojo playing ocarina](/assets/content/docs/creatives/mojo-playing-ocarina.png)

<p align="center" class="good-work-mojo-msg"><i>Oh wow!<br/>You tweaked it a lot, Mojo reader.</i></p>

---

<p align="center" class="inspiring-quote">"On Earth and Space, he has all the tricks."</p>

<p align="right" class="inspiring-quote-author">― ▒▒█𝚃𝙾𝙿 𝚂𝙴𝙲𝚁█𝚃 // 𝚂𝙲𝙸 // 𝙽▒▒▒▒𝙾𝙵𝙾𝚁𝙽</p>

</llm-exclude>
