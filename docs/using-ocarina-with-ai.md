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

This page describes a concrete working setup: a full test cycle built and maintained alongside Claude Code and Ocarina. The system under test is the
public Katalon CURA demo. The goal here is purely descriptive: what files exist, what each one does, how they compose.

[📖 Get the AI example as a reference.](https://github.com/mojo-molotov/ocarina-with-ai-example)

## The three spiritual stones

1. A `CLAUDE.md` file at the project root.
2. A `skills/` directory containing one `<name>/SKILL.md` per procedure.
3. A verification rule: every claim about SUT behaviour must come from observation (a probe, a `gh api`, a `curl -v`), never from inference.

## `CLAUDE.md`

The file encodes the rules that don't change between turns.

**Security testing is functional and static, never active.** The whole black-hat family (saturation, persistence, lateral access, BFCache exposures)
is bound by this rule. No injection payloads. No request crafting. No DevTools DOM manipulation. Every attack scenario must be reachable through a
normal UI motion.

**Use constants.** If a value has a name (`DEMO_USERNAME`, `LOGIN_URL`), don't inline it.

**Dataset construction is a human decision.** When the assistant proposes adding or modifying a dataset, the run does not automatically follow.

**Verify SUT behaviour empirically.** A claim about what CURA does comes from a probe that captured the HTML, a `gh api` that read the deployed PHP,
or a `curl -v` that read the headers. Never from inference.

Each rule carries a one-line _why_ (usually a past incident) so the assistant applies judgment at the boundary instead of pattern-matching the rule.

## `skills/`

Each skill is a single Markdown file, with YAML frontmatter (`name`, `description`) and a body that walks one procedure end-to-end. They cluster into
eight families.

### Review (12)

Static reads of the codebase or specs. Skills surface findings; the user applies.

- `review-spec-gaps` reads the FRD the way a QA analyst would and surfaces clarification questions.
- `review-watcher-misuse` checks every `watcher.report(...)` call against the negative-only convention.
- `review-compartmentalisation-leaks` finds URLs outside `src/constants/urls.py`, selectors outside POMs, magic numbers inline.
- `review-report` classifies every FAIL (body, setup, teardown) and SKIP (static, smoke-gate, setup-error, cycle-policy) for one run.
- Plus: `review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers`, `review-comment-drift`,
  `review-suite-stability`, `review-intent-collisions`, `review-watcher-emissions`.

### Analyse (4)

- `analyse-flakiness` widens the transient-error net so every exception retries; chronic deaths after N replays are very likely real flakes.
- `analyse-fixture-flakiness` instruments the setup/teardown boundary so cross-test contamination becomes visible.
- `analyse-watcher-flakiness` runs the suite with and without each watcher, across a poll-interval sweep.
- `analyse-screenshot-flakiness` groups screenshots by `(test, step, browser)` and looks for differing behaviours.

### Black-hat (6)

- `business-attack-ideation` tries to bring the product down.
- `incoherence-attack-ideation` covers combinations of actions that are individually allowed but incoherent as a set (e.g., the same person booking
  hotels in two cities with a time window that makes the travel physically impossible).
- `persistence-attack-ideation` covers repeated attempts to perform an action blocked by the SUT.
- `permission-appropriateness-audit` reads the access model and asks _"is this parity intentional?"_
- `bfcache-exposure-ideation` identifies BFCache attacks.
- `lateral-resource-ideation` borrows the spirit of IDOR but stays restricted to address-bar manipulation (no request interception, no proxy).

### Comprehend (4)

- `assess-test-base` catalogues the test base.
- `assess-ecosystem` does a bounded research pass over public sources, capped by a token budget (one-third of remaining tokens by default).
- `understand-sut-constraints` maps the SUT-side bounds that cause the _test code_ to misbehave under parallelism (e.g., max simultaneous sessions per
  user).
- `understand-ocarina` walks the documentation.

### Pick (3)

Pick the right files from run output.

- `pick-screenshots`, `pick-logs`, `pick-reports`.

### Author (7)

Workflow skills that produce a deliverable.

- `empiricism`: verify before encoding; never overwrite an intentional-fail gap test.
- `write-a-probe`: throwaway Python script in a gitignored directory.
- `extend-coverage`: extends test coverage based on existing assets.
- `update-frd-and-tests`: propagates a specification update.
- `manual-reproduction-guide`: produces a manual reproduction scenario.
- `manage-backlog`: manages a backlog (`BACKLOG.md`).
- `pr-report`: produces a PR-type-aware report (refactor, test strategy, bug fix, docs).

### Refactor (2)

- `refactor-fragmentation` applies the DRY principle according to the user's preferences.
- `introduce-pom-retries` produces POM-internal retries to fight flakiness, with the two-test split: a _first-try_ variant (no retry, intentional fail
  until the anomaly is corrected) and a _with-retries_ variant (passes via POM retries, keeps coverage stable).

### State (1)

- `question-state`: inspects the SUT's environmental state (warm vs cold dyno, leftover artifacts, browser-profile cleanliness, workers concurrency,
  recent updates, time-bound contention, etc.).

## Recurring chains

Skills compose. A few chains that come up often:

**When the suite isn't green:**

1. `review-report` classifies each incident (FAIL: body, setup or teardown; SKIP: static, smoke-gate, setup-error or cycle-policy).
2. Depending on the incident class, one of `analyse-flakiness`, `analyse-fixture-flakiness`, `analyse-screenshot-flakiness` follows.
3. `write-a-probe` isolates the root cause.
4. The finding is recorded in `IDENTIFIED_GAPS.md`, in the FRD, or in a scenario comment.
5. The probe is deleted.

**When a black-hat scenario looks promising:**

1. `empiricism` verifies CURA's current behaviour.
2. `extend-coverage` writes the test, often as an intentional fail, until the SUT corrects the behaviour.

**When a spec changes:**

1. `update-frd-and-tests` updates the FRD first, with a one-sentence reason.
2. Tests are then adapted.
3. If a gap test is affected by the fix, it is reframed (assertion inverted, test renamed, strategy-doc category moved from intentional-fail to
   pass-everywhere) rather than simply edited to turn green.

**When a new Ocarina primitive is needed:**

1. `understand-ocarina` consults the Holy Book first.
2. Writing comes after.

## Discipline

Several patterns repeat across every procedure.

**Surface, do not apply.** Every skill ends the same way: print the catalogue, stop, let the user decide.

**Empirical, not assertive.** Every SUT-behaviour claim is backed by an observation, cited in place, dated. The ritual phrase: _"Fair point, I'm
assuming. Let me verify empirically."_ It triggers a `write-a-probe`; the probe captures the truth; the finding lands; the probe is deleted.

**Gap tests are reframed, not turned green.** When CURA fixes a §9 gap, the intentional-fail test cannot just be edited to match the new behaviour.
The discipline: invert the assertion, rename the test, move its strategy-doc row from intentional-fail to pass-everywhere, update `IDENTIFIED_GAPS.md`
with the resolution date. All in one motion via `update-frd-and-tests`.

**Watcher emissions are always negative signals.** A watcher emitting _"login succeeded"_ breaks the contract. `review-watcher-misuse` audits the
callbacks; `review-watcher-emissions` reads run output knowing every emission is, by convention, undesirable.

**Horizontal scaling first.** When a coordination layer is proposed, the question is _"does this work at one process, three processes, N processes?"_
In-memory state at the Ocarina-worker level is rejected by construction. Distributed primitives only.

**Identify generated artifacts by mtime.** Screenshots, logs, reports all carry random UUID suffixes. The three `pick-*` skills exist to prevent
lexicographic sorting.

## What this setup isn't

This setup does NOT:

- Generate tests autonomously.
- Patch hallucinations in CI. A failing test triggers `review-report` and an `analyse-*` skill.
- Rewrite the spec. The FRD is edited only via `update-frd-and-tests`, with a revision-history line.
- Run active security tests. Not now, not ever.

## Exposed resources

- https://mojo-molotov.github.io/ocarina-holy-book/llms.txt
- https://mojo-molotov.github.io/ocarina-holy-book/llms-full.txt
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.md
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
