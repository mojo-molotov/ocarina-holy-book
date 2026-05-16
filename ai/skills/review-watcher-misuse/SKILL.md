---
name: review-watcher-misuse
description:
  "**Static review of every Ocarina `Watcher` callback** to check it respects the convention: *a watcher reports only the undesirable; a watcher never
  informs of something positive*. The skill reads each registered watcher's callback source, examines every `watcher.report(...)` call site, and flags
  any that describes a *positive* observation ('login succeeded', 'form rendered', 'page loaded correctly'), an *unconditional* report (firing every
  poll cycle regardless of state — that's not a watcher, that's a log spammer), or a report whose message is neutral / informational rather than
  warning-shaped ('user is on the home page'). Surfaces misuses with the recommended fix: re-shape into a real assertion in the test body if it's
  positive, drop the call if it's noise, or rewrite the message if it's just phrased wrong. Use whenever the user asks to review watchers, audit
  watcher convention compliance, vet a PR that introduces a watcher, or sanity-check the watcher catalog before a release."
---

# Review watcher misuse — the negative-signal-only rule

A static-review skill. The Ocarina convention:

> **A watcher reports the undesirable. A watcher never informs of something positive.**

Watchers are background daemons that run alongside the test chain. They share the driver, fire on a poll, and emit log lines + screenshots through
`watcher.report(msg)`. Each emission carries semantic weight (see `review-watcher-emissions`): readers downstream interpret an emission as _"something
the team should know about, in the negative"_. A watcher that emits positive observations corrupts that contract — every downstream consumer
(`review-report`, `review-watcher-emissions`, the CI summary, the human reader) now has to second-guess each emission's polarity.

The skill walks each watcher's source and checks: _are the `report()` calls strictly negative-shaped, and only fired when the negative condition is
observed?_

## The four misuse shapes

### 1. Positive-shaped report message

The callback observes a _normal_ state and reports it as if it were noteworthy:

```python
# WRONG
def watch_login_success(watcher: Watcher) -> None:
    if HomePage(watcher.driver).is_loaded():
        watcher.report("Login succeeded — user is on the home page")
```

A login succeeding is what the test asserts. The watcher reporting it means every successful login is _also_ a watcher emission, which inverts the
emission's downstream meaning ("an emission = something undesirable" → no longer true). Fix: this isn't watcher work; if the assertion isn't already
in the test body, add it there.

### 2. Unconditional / status-line report

The callback emits on every poll cycle regardless of what it observed:

```python
# WRONG
def watch_page(watcher: Watcher) -> None:
    watcher.report(f"Currently on {watcher.driver.current_url}")
```

This is a `logger.info` written into the wrong primitive. It generates an emission burst (one per `poll_interval`) and floods every report. Fix: if
the trace matters, use the logger directly; if it doesn't, drop the watcher.

### 3. Neutral / informational message (negative _event_, but worded as observation)

The callback observed something undesirable, but the message is too soft to read as a warning:

```python
# WRONG (the event is undesirable; the message reads positive)
def watch_cookie_banner(watcher: Watcher) -> None:
    banner = CookieBanner(watcher.driver)
    if not banner.is_visible():
        return
    watcher.report("Cookie banner is visible")    # neutral observation
```

The emission _is_ of an undesirable element (a banner that blocks UX), but the message frames it as a status update. Downstream readers can't tell the
polarity. Fix: rephrase to make the negative shape explicit — _"Undesirable: cookie banner intrudes on user view"_ or _"Cookie banner detected (blocks
main content)"_.

### 4. Mixed-polarity callback (positive _and_ negative paths)

The callback emits one report for the negative case and another for the positive case:

```python
# WRONG
def watch_session(watcher: Watcher) -> None:
    if SessionExpiredBanner(watcher.driver).is_visible():
        watcher.report("Session expired banner appeared")
    elif HomePage(watcher.driver).is_loaded():
        watcher.report("Session is healthy")
```

The negative path is fine; the positive path violates the convention. Fix: delete the positive branch — the absence of an emission is the "healthy"
signal.

## Subordinate checks (still relevant, but downstream)

The skill's primary axis is the negative-only convention. While reading the callback, it also surfaces (without making them the headline):

- **The callback should be exception-safe.** Per the Ocarina contract, exceptions in the callback are silently suppressed. The callback should still
  be written defensively (early `return` on missing element, no None deref). A callback that _relies_ on the suppress is one selector drift away from
  firing zero times forever — hand off to `analyse-watcher-flakiness §2`.
- **The callback should use `watcher.cache` for dedup.** Otherwise the same negative observation emits on every poll cycle. The dedup is a signal-to-
  noise tool; without it, even a correctly-negative watcher will flood the report. Hand off to `analyse-watcher-flakiness §5`.
- **The callback should _only read_ the driver.** A callback that clicks, types, or navigates is a test-chain action wearing a watcher's clothing.

These get a one-line mention if observed, but they are not what this skill is for.

## Procedure

### Step 1 — Inventory the watchers

```bash
grep -rn "Watcher\[\|watchers=" src
```

If empty, the review is empty — surface that. _"No watchers registered; nothing to audit."_ The skill stays useful as a pre-flight checklist for the
next watcher to land in a PR.

For each watcher found: name, callback file:line, attached scenario(s).

### Step 2 — Read each callback in source

For each callback:

- Find every `watcher.report(...)` call site (could be multiple per callback).
- Find the conditional that gates each call (the `if`, `elif`, or unguarded straight-line code).
- Read the message string passed to `report()`.

### Step 3 — Apply the four misuse checks

For each `report()` call:

| Check                                                  | Decision rule                                                                                                     |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| §1 Positive-shaped message                             | Does the message describe a _normal_/_expected_/_successful_ state? → MISUSE.                                     |
| §2 Unconditional emission                              | Is the call guarded by _nothing_, or by a condition that's nearly always true? → MISUSE.                          |
| §3 Neutral / informational message on a negative event | Is the gate negative-shaped (e.g. banner visible, error in console) but the message neutral? → MISUSE (re-word).  |
| §4 Mixed-polarity callback                             | Are there multiple `report()` calls, one of which is on a positive branch? → MISUSE (delete the positive branch). |

A `report()` call that passes all four is **convention-compliant** — silent in the report.

### Step 4 — Surface the findings

````markdown
# Watcher-misuse review

## Watchers reviewed

- `<name>` — callback at `<file>:<line>`, attached to `<scenario(s)>`.
- ... (or "none — nothing to audit; checklist applies to future PRs")

## Misuses

### `<watcher name>` — `<file>:<line>`

- **Misuse class**: §1 positive-shaped | §2 unconditional | §3 neutral wording | §4 mixed polarity.
- **The call site**:
  ```python
  <verbatim quote of the report() line + its guard, 3–5 lines of context>
  ```
````

- **Why it's a misuse**: <one sentence>.
- **Recommended fix**:
  - §1 → move the check into the test body as an assertion; delete the watcher branch (or delete the watcher if that was its only purpose).
  - §2 → drop the call; if the trace matters, use the logger directly.
  - §3 → rephrase the message to be explicitly warning-shaped (suggested: `<rephrased message>`).
  - §4 → delete the positive branch.

(One block per misuse.)

## Subordinate observations (not misuses per se, surfaced for the user's awareness)

- `<watcher name>`: no `watcher.cache` dedup → emission flood risk; cross-ref `analyse-watcher-flakiness §5`.
- `<watcher name>`: callback writes to the DOM (`.click()` at `<line>`) — that's an action, not an observation. Rewrite as a test-body step.

## Cross-references

- Ocarina convention: see `<gitignored>/ocarina/.../watcher.py` docstring.
- Downstream skill: `review-watcher-emissions` (reading emissions in run output).
- Adjacent audit: `analyse-watcher-flakiness` (concurrency + reliability).

## Verdict

<one-line: <N> misuses across <K> watchers / all watchers compliant / no watchers registered (checklist applies to PRs)>.

```

Print the findings. Do not edit any file.

### Step 5 — Stop. The user decides.

Each misuse can resolve as:

- **Fix the watcher** — apply the recommended rephrase / branch deletion / etc. The user (or a follow-up edit motion) writes the change.
- **Remove the watcher entirely** — if every `report()` call was misuse, the watcher has no remaining purpose.
- **Defer** — pre-existing misuse the team isn't ready to refactor; record it.

## Hard rules

- **Negative-only is the headline rule.** A callback that emits a positive observation is a misuse regardless of how well-engineered the rest of the
  callback is.
- **Absence of emission is the "all good" signal.** A correctly-written watcher reports *nothing* when everything is fine. The reader's downstream
  expectation depends on this.
- **Read the message string, not just the gate.** A negative gate with a neutral message (§3) is still a misuse — the downstream reader sees the
  message, not the condition.
- **Don't fix in place.** Static review surfaces; the user applies. A watcher rewrite changes runtime behaviour and is authoring data (per the
  "Datasets are authoring decisions" rule — same logic applies to observability instrumentation).
- **One misuse per finding.** A `report()` call that's §1 *and* §3 (positive message that's also informational) collapses to "delete or rewrite" —
  the headline is §1.

## When to run this skill

- A PR introduces a new watcher — vet the convention before merging.
- During a periodic codebase review — watchers can drift over time, especially if a callback is edited by someone unfamiliar with the convention.
- Before invoking `review-watcher-emissions` on a run — if the watchers themselves are non-compliant, the emissions reading is confused at the source.
- After a `review-suite-stability` audit flags an unexpected emission burst — the burst may be a §2 unconditional emission, not a real signal.
- Onboarding — the convention is non-obvious; a contributor's first watcher is a high-risk PR.

## What this skill does NOT do

- It does not edit any callback. Static review surfaces; the user applies.
- It does not audit the watcher's concurrency / reliability behaviour. Use `analyse-watcher-flakiness`.
- It does not read run-time emissions. Use `review-watcher-emissions`.
- It does not classify FAIL / SKIP incidents in a report. Use `review-report`.
- It does not write a new watcher. Authoring is a scenario-design step; this skill only audits.
- It does not include attack-shape suggestions in any rewrite. Per `CLAUDE.md` → "Security testing is functional and static — never active".
```
