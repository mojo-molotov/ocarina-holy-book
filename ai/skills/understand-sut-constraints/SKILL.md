---
name: understand-sut-constraints
description:
  "**Map the SUT-side constraints that shape how tests can safely run in parallel** — the bounded resources and global-state interactions that, if
  hit, cause undefined behaviour in *the test code itself* rather than in the app under test. Classic examples: max concurrent sessions per account (a
  heavily-parallelised suite reuses the demo account; at saturation, the SUT rejects new logins and the test code mistakes that for an app bug); OTP
  login where the matching information is coarse (time-windowed with poor precision) so parallel tests race for the same code; per-tenant rate limits;
  database-row locks on shared records; deployment-wide write quotas. For each constraint, the skill walks: *is it specified anywhere? if not, is it
  an anomaly or a deliberate-but-undocumented limit?* and then proposes mitigations **aware of Ocarina's horizontal-scaling discipline — applied where
  shared scarcity exists**: when the fleet contends on a finite SUT-side resource, never in-process state at the scale of one Ocarina worker (that
  breaks at the next scale-out), always distributed primitives (a Redis-backed counter, a distributed lock, a delta-timer reservation) at the scale of
  the whole test fleet; when no shared scarcity applies, a worker-local in-memory cache is acceptable *only* if its keys are uniquely generated and
  the generation mechanism is thread-safe enough for the contention level. Use whenever the user asks to understand the SUT's parallel-safety
  envelope, find constraints that could flake the test code itself, audit shared resources for race conditions, or design distributed coordination for
  a flaky-under-parallelism test."
---

# Understand the SUT's constraints — what the app limits, the tests must coordinate

A comprehension skill. Most flakiness skills (`analyse-flakiness`, `analyse-fixture-flakiness`, `analyse-watcher-flakiness`) look at where the _test
code_ breaks. This skill looks one layer up: where the **SUT itself imposes constraints** that, under parallel-test load, cause the test code to
break.

The defining shape: the SUT is fine. The test fleet is fine in isolation. But the _combination_ — N parallel tests against a SUT with bound X — hits
the bound and the test code observes "weird behaviour from the app" that isn't the app's fault. It's the tests' fault for not coordinating around X.

The mitigation discipline:

> **Ocarina prioritises horizontal scaling — applied where the fleet contends on a finite SUT-side resource.**
>
> When such contention exists, coordination state never lives in a single Ocarina process's memory. Today's `--workers 3` becomes tomorrow's
> distributed CI matrix becomes the next-year's elastic fleet. Anything that works at one scale and breaks at the next is a regression waiting to
> happen.
>
> When no such contention exists for the traversed use case, the discipline relaxes: a worker-local in-memory cache is acceptable. The relaxation has
> two non-negotiable conditions — **uniquely generated keys** (no two workers collide on the same slot) and a **thread-safe-enough generation
> mechanism** (the concurrency level the cache will see does not race the key-generation path). Both conditions must be confirmed deliberately, not
> assumed.

So: distributed primitives when the fleet shares scarcity (a Redis-backed counter, a distributed lock, a reservation system with delta-timing) — the
test fleet coordinates _as a fleet_, not as a process. Worker-local in-memory only when no shared scarcity applies _and_ the key-generation /
thread-safety pair holds.

The two questions — _"is there shared scarcity?"_ and _"if not, are keys unique and generation thread-safe enough?"_ — are the gates. Skipping them
and reaching for in-memory because it's convenient is the hidden regression: it works under today's load, fails when the SUT (or the parallelism)
crosses a threshold that was never explicitly checked. A concrete shape: a session-cache keyed off a process-local counter is fine for a SUT with no
session cap; the same shape, against a SUT that does cap concurrent sessions per account, contends silently across workers and breaks. Same code, two
SUTs, two verdicts — because the gates resolve differently.

## The seven SUT-constraint shapes

For each, the comprehension lens: _does the SUT have this constraint? is it documented? if it bites under parallelism, what's the distributed
mitigation?_

### 1. Max concurrent sessions per account

The SUT caps how many sessions a single account can hold open simultaneously. Tests parallelising on a shared demo account hit the cap.

- **Concrete example**: CURA's demo account (`John Doe`) is shared across every parallel worker in `ocarina-with-ai-example`. If CURA enforces a
  session cap (verify per `empiricism`), heavy `--workers` runs would saturate it. The project's current load doesn't seem to hit it — note as
  "currently within envelope; capacity unknown".
- **Test-code symptom**: a new login attempt that should succeed gets rejected (or returns the wrong page); the test reads this as "login broken" but
  the app is doing exactly what it was told.
- **Mitigation**: distributed counter of active sessions per account; tests acquire a slot before logging in, release it on logout/teardown.

### 2. Time-windowed coarse identifiers (OTP, daily codes, hourly tokens)

The SUT issues identifiers whose uniqueness depends on time at coarse precision (seconds, minutes). Two parallel tests requesting an OTP "now" can
collide on the same code.

- **Example shape**: OTP tied to the current minute; if two tests trigger OTP issuance in the same minute, both may receive the same code, both may
  consume it, behaviour becomes undefined.
- **Test-code symptom**: OTP-consume test fails for "wrong code" when the code was technically valid for the other test that just consumed it.
- **Mitigation**: distributed lock around (account × time-window); tests serialise their OTP issuance per window. Or: delta-time their starts so no
  two tests fall in the same window. The choice depends on how much serialisation the fleet can tolerate.

### 3. Per-tenant / per-account rate limits

The SUT throttles requests at a rate that's fine for one user but tripped by N parallel test workers all driving as one user.

- **Test-code symptom**: tests pass solo, fail at higher worker counts with 429 / generic errors that don't match the app's normal failure UI.
- **Mitigation**: distributed token bucket; workers acquire tokens from the bucket at a rate compatible with the limit.

### 4. Shared-row locks on common resources

The SUT serialises writes to a shared row (e.g. the shared demo profile, a singleton config record). Parallel writers contend; one wins, others wait
or fail.

- **Concrete example**: the demo account's profile / history is shared; tests editing it in parallel may step on each other. This is closer to
  `§A-ENV-1` (rapid-POST shared-dyno contention; CURA gap inventory) — confirm whether the contention is row-locking or transport-layer.
- **Mitigation**: distributed lock per shared resource; tests acquire-and-release around the contested operation. Or: partition by test-owned sub-rows
  if the SUT's data model allows.

### 5. Deployment-wide write quotas

The SUT (or its hosting tier) caps writes per day / hour. Tests that create many records cumulatively exhaust the quota even though no single test is
above the limit.

- **Concrete example**: not directly observed; Heroku's eco tier has its own dyno limits but no per-account write quota that the project is aware of.
- **Mitigation**: distributed write counter; once quota approached, defer or skip non-essential tests. Cleanup tests to release quota where possible.

### 6. Per-resource exclusivity (a slot, a calendar, a desk)

The SUT models a resource that can only be held by one user at a time. Parallel tests targeting the same slot collide.

- **Concrete example**: in the worked example (<https://github.com/mojo-molotov/ocarina-with-ai-example>), the `saturation_booking` test intentionally
  exercises this — different tests for different dates avoid the collision. Adding new appointment tests requires the same discipline.
- **Mitigation**: distributed reservation of slots; tests claim their slot from a pool before driving the SUT.

### 7. Eventual-consistency windows

The SUT's read-after-write isn't immediate (replication lag, cache, async indexing). Parallel tests that write-then-read race against the propagation.

- **Test-code symptom**: a test that creates a record then immediately verifies it appears in a list passes alone (the lag is below the test's wait
  budget) but flakes under load (the system is slower under load, lag grows).
- **Mitigation**: distributed coordination that waits _empirically_ for the write to propagate (poll until visible, with a budget); avoid in-process
  fixed sleeps that don't scale.

## The horizontal-scaling discipline

First gate, before any mitigation question: **does the fleet share scarcity on this constraint?** If two workers cannot interfere — because the SUT
imposes no bound the test traversal touches, because each worker owns disjoint data, because the resource is effectively unbounded for the use case
walked — then the constraint isn't a coordination problem and a worker-local in-memory cache is acceptable. In that case, only the cache-correctness
sub-gate applies:

- **Are the cache keys uniquely generated?** Two workers landing on the same key by accident is a collision waiting to happen — even without a SUT
  bound. Process IDs, run IDs, worker IDs, deterministic-per-test seeds — pick one that the project actually carries; don't invent.
- **Is the key-generation mechanism thread-safe for the concurrency the cache will see?** Within a single process, this is GIL-friendly Python code,
  `threading.Lock`, `itertools.count()` (atomic), or similar. Across workers on the same machine, file locks. Across machines, you're already in
  distributed-primitive territory — which means the first gate's verdict was wrong and you need to re-walk it.

When the fleet _does_ share scarcity — a session cap, a slot pool, a per-tenant rate limit, a write quota — the mitigation question opens. For every
mitigation, ask:

- **Does this state live in one Ocarina process?** If yes — wrong. Today the test fleet is one process with `--workers 3`; tomorrow it's three
  processes on three runners. In-process counters / locks / queues evaporate the moment the second process spins up.
- **Does this state live in a distributed primitive?** Redis is the canonical example; the project's memory may name others (verify before
  recommending). Distributed locks (Redlock or equivalent), distributed counters, distributed reservation systems.
- **Does the primitive itself have a lifecycle?** Locks must time out so a crashed worker doesn't hold them forever. Counters must reset on a known
  boundary (start of run, end of day).
- **Does the primitive add a new flake surface?** A Redis outage means the entire test fleet stalls. Surface that as a known cost and document the
  fallback.
- **Is the primitive part of the test infrastructure, not the SUT?** The SUT is unchanged. The coordination layer lives next to the test runner.

## Procedure

### Step 1 — Inventory the SUT-side constraints

Walk the FRD, the SUT's public docs (per `assess-ecosystem`), and the existing gap inventory for clues:

```bash
grep -rn -i "limit\|cap\|max\|quota\|rate\|throttle\|concurrent\|session\|otp" .
gh api repos/<sut-org>/<sut-repo>/contents/<relevant php> --jq '.content' | base64 -d
```

For each constraint candidate, capture: **what bound, where it's enforced, where it's documented (if anywhere), whether the project's current
parallelism load has approached it**.

### Step 2 — Walk the seven shapes against the SUT

For each shape × SUT:

- Does the SUT have this constraint? (Verify per `empiricism` if uncertain.)
- Is it specified — in the FRD, the SUT's public docs, or the gap inventory?
- Is the test fleet's current parallelism load below or above the threshold?
- If above (or close), is the symptom currently masquerading as something else (a §A-ENV-1 transport flake, an unexplained intermittent failure)?

### Step 3 — Classify per constraint

For each constraint found:

- **Specified, within envelope** — no action. Document the awareness.
- **Specified, near envelope** — surface; the team may want to plan coordination before it bites.
- **Specified, over envelope** — coordination needed; surface with mitigation proposal.
- **Unspecified, observed** — anomaly question first ("is this intended?"), spec update via `update-frd-and-tests` if confirmed, mitigation after.
- **Unspecified, theoretical** — note for future; do not propose mitigation yet.

### Step 4 — For each over-envelope constraint, propose a distributed mitigation

For each, sketch (don't implement):

- **Primitive**: distributed counter | distributed lock | distributed reservation | distributed token bucket | empirical-propagation wait.
- **Backing store**: Redis (or whichever the project standardises on — verify with the user; this is infra, not a unilateral pick).
- **Lifecycle**: acquisition / release / timeout / reset boundary.
- **Failure mode**: what happens if the primitive is unavailable; explicit fallback (skip, fail-loud, run unsafely with a warning).
- **Horizontal-scaling check**: confirm the mitigation works at 1 process, 3 processes, N processes — no in-process shortcuts.

### Step 5 — Surface the comprehension report

```markdown
# SUT-constraint comprehension — `<SUT>` (<date>)

## Constraints identified

### `<constraint name>` (shape §<n>)

- **What**: <one-sentence description>.
- **Enforced by**: <SUT location | hosting tier | inferred>.
- **Specified**: <FRD §X | public doc URL | not documented>.
- **Current parallelism load vs threshold**: <within | near | over | unknown>.
- **Currently masquerading as**: <`§A-ENV-1` | nothing | unknown>.
- **Anomaly question** (if unspecified): _"Is this constraint intentional, or is the SUT silently capping behaviour?"_
- **Mitigation proposal** (if over envelope):
  - Primitive: <distributed counter | lock | reservation | token bucket | empirical wait>.
  - Backing store: <user-confirmed infra, e.g. Redis>.
  - Lifecycle: acquire `<when>` / release `<when>` / timeout `<duration>` / reset `<boundary>`.
  - Failure mode: <skip | fail-loud | run unsafely with warning>.
  - Horizontal-scaling check: <explicit confirmation: works at 1 / 3 / N processes>.

## Constraints suspected but unconfirmed

- `<name>`: <hypothesis>. Verify via `empiricism` / `assess-ecosystem` before mitigating.

## Currently safe — within envelope, documented for awareness

- `<name>`: <current load / threshold / margin>.

## Anti-patterns to avoid

- In-process counter / lock / queue for any SUT-shared constraint — breaks the moment Ocarina scales horizontally.
- Worker-local in-memory cache reached for without first answering both gates (_"is there shared scarcity?"_ and _"if not, are keys unique and
  generation thread-safe enough?"_) — works today, fails silently when the SUT or the parallelism crosses an unchecked threshold.
- Hard-coded `sleep()` waits for eventual-consistency lag — doesn't scale, brittle to environment.
- "Solve at the test level" hacks that paper over an unspecified SUT bound rather than first asking whether the bound is intentional.

## Cross-references

- Related skills: `analyse-flakiness` (test-body retry classification), `analyse-fixture-flakiness` (boundary instrumentation),
  `business-attack-ideation` (saturation as deliberate attack), `assess-ecosystem` (third-party constraints from docs), `introduce-pom-retries`
  (POM-retry candidates that turn out to be SUT bounds belong here, not in a retry layer).
- `the gap inventory (environmental section)` — current environment artifacts (some may be SUT-constraint symptoms in disguise).
- `using-ocarina-with-ai` → _"Distributed when scarcity is shared"_ — the one-line summary of this skill's discipline.

## Recommended next motions

- For each anomaly question: `empiricism` to verify, then `update-frd-and-tests` to specify (if confirmed) or the gap inventory to file (if it's a SUT
  defect).
- For each mitigation proposal: design discussion with the team — distributed infra is a project-shape decision, not a unilateral one. Author the
  coordination layer as a separate PR with the constraint comprehension cited.
- For each currently-safe constraint: revisit when the test fleet's parallelism grows.

## Verdict

<one-line: N constraints over envelope (mitigation needed), K within envelope, J anomaly questions for the team, nothing material>.
```

Print the report.

### Step 6 — Stop. The user decides.

Each constraint resolves as:

- **Specify** — extend the FRD / the gap inventory with the deliberate bound.
- **Mitigate** — design the distributed coordination layer (a separate PR; this skill surfaces the need, doesn't author the layer).
- **Defer** — currently within envelope; revisit when parallelism grows.
- **Discuss** — infra decision needs team / stakeholder input.

The comprehension is the deliverable. The mitigation is a follow-up motion.

## Hard rules

- **Horizontal scaling applies where the fleet shares scarcity.** When the SUT bounds a resource the fleet contends on, no in-process state for that
  coordination — the mitigation must be valid at 1 process, 3, and N. When no shared scarcity applies to the traversed use case, worker-local
  in-memory is acceptable — _provided_ the cache-correctness gates pass (uniquely generated keys + thread-safe-enough key generation). The two gates
  ("shared scarcity?" then "if not, keys + thread-safety?") are walked explicitly, never skipped because in-memory was convenient.
- **Ask the spec question first.** _"Is this constraint specified?"_ before _"how do we work around it?"_. An undocumented bound may be a SUT bug that
  should be fixed in the SUT, not papered over in the tests.
- **Mitigations are infrastructure, not test code.** They live in a coordination layer (Redis, distributed lock service, reservation system), not
  inside a scenario or a connector. The skill surfaces the need; authoring the layer is its own project.
- **Verify constraints empirically before mitigating.** A theoretical constraint that doesn't actually bite is a waste of infra complexity. Per
  `empiricism`.
- **Per `CLAUDE.md`: security testing is functional and static — never active.** This skill stays on the comprehension side; it does not propose load
  testing, stress probes, or any active fuzzing of the SUT's limits.
- **Cross-reference `the gap inventory (environmental section)` carefully.** Some current environment artifacts may be SUT-constraint symptoms
  disguised as transport flakes. The comprehension pass can re-classify them; the re-classification is a `update-frd-and-tests` motion.
- **Backing-store choice is the user's.** This skill names "Redis" as the canonical example because it's the common default; the actual primitive
  depends on the project's infrastructure. Confirm with the user before recommending a specific store.

## When to run this skill

- Before scaling up parallelism in CI (more workers, more runners).
- After a `review-suite-stability` audit surfaces flakes that scale with parallelism (the more you parallelise, the more you flake) — that's the
  signature of an SUT-side constraint.
- When introducing a new feature that touches a shared resource (a singleton config, an OTP, a quota'd endpoint).
- When considering moving to a CI matrix with multiple runners — the in-process assumptions of the current `--workers` model break.
- Onboarding — a constraint map is part of the mental model.

## What this skill does NOT do

- It does not author the coordination layer. Surfaces the need; authoring is a separate project.
- It does not run load tests, stress probes, or active SUT investigation. Stays on the comprehension / static side.
- It does not unilaterally pick the backing store (Redis vs alternative). Names a canonical example; the choice is the user's.
- It does not modify the SUT. SUT-side fixes are the SUT team's domain.
- It does not encode tests around constraints. Tests that intentionally exercise a constraint (saturation tests) are `business-attack-ideation` /
  `extend-coverage` territory.
- It does not file the gap inventory entries directly. Cross-references are recommended; entries are a follow-up via `update-frd-and-tests`.
