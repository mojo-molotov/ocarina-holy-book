---
name: review-watcher-emissions
description:
  "**Watcher emissions hide in plain sight in reports and logs** — an Ocarina `Watcher` doesn't FAIL the test, doesn't SKIP the test, and doesn't fit
  any of the standard incident classes. It just *quietly emits* a log line + screenshot via `watcher.report(msg)` while the test passes. The result is
  a stray screenshot file in the burst that 'doesn't look like it belongs', or a log line that doesn't match any test step, or an entry in the report
  that's neither PASS, FAIL, nor SKIP. The skill teaches the reader to **recognise watcher emissions as the negative signals they are**, because — by
  Ocarina convention — *a watcher never reports something positive*. A watcher exists to flag the undesirable; if it fired, something undesirable was
  observed, even if the test still passed. Walks the report + log + screenshot set looking for these emissions, cross-references each one to its
  watcher, and surfaces them as **deferred-investigation items** that the standard `review-report` pass misses. Use whenever the user asks to audit
  watcher output, look for hidden negative signals, review the 'extra stuff' in a report, or sanity-check that nothing watcher-emitted was overlooked."
---

# Review watcher emissions — the quiet negative signals

A reading skill complementary to `review-report`. That skill classifies the **explicit** incident axes (FAIL × {body, setup, teardown}, SKIP ×
{static, smoke-gate, setup-error, cycle-policy}). Watcher emissions sit _outside_ those axes — they don't fail the test, they don't skip it, and the
standard report headline doesn't surface them.

But they matter, because of the Ocarina convention:

> **A watcher only reports the undesirable. A watcher never informs of something positive.**

This is the discipline that gives watcher emissions their semantic weight. A `watcher.report("login form rendered correctly")` would be a misuse of
the primitive — that's an assertion's job. A watcher's `report()` always means _"I saw something the team should know about, in the negative"_: a
cookie banner intruded, a console error appeared, a session-refresh toast slid in, a deprecation warning rendered, the page changed height
unexpectedly. The fact that the test _still passed_ doesn't soften the signal; it just means the body wasn't structured to be affected by what the
watcher saw.

The skill walks a run's outputs hunting for those quiet emissions and re-classifies them as **deferred investigation items**.

## Where watcher emissions hide

Five surfaces, in order of where they're easiest to miss:

### 1. Stray screenshot files in the burst

The screenshot folder mixes:

- Failure screenshots (taken by the framework hook on FAIL).
- Step screenshots (if the suite is configured to capture per-step).
- **Watcher screenshots** (taken by `watcher.report()`).

A burst of 4 shots around a test failure that includes a _fifth_ shot timestamped during the test body — that fifth shot is probably the watcher. It's
not "extra clutter". It's the quiet negative signal.

### 2. Log lines without a step ID

Most Ocarina log lines tie to a test step. Watcher log lines come from a _different thread_ (the daemon) and don't carry the same context. Look for:

- Lines whose source attribute names the watcher (`watcher=<name>` or similar).
- Lines whose level is INFO/WARN but whose message has the shape `<watcher name>: <observation>`.
- Lines that land _between_ two consecutive test-body lines, with a timestamp in the polling cadence (every `poll_interval` seconds — see
  `analyse-watcher-flakiness`).

### 3. Report entries that aren't PASS / FAIL / SKIP

If the run's JSON / DOCX has a section, attachment, or row that doesn't map to any test result — that's almost certainly a watcher attachment. Many
Ocarina-style reports embed watcher reports as attachments on the _containing test_, but the attachment is the negative signal, not the test status.

### 4. Cache-size or "things observed" counts at stop

Per `analyse-watcher-flakiness`, instrumentation can log `len(watcher.cache)` at `stop`. A non-zero cache means the watcher _saw distinct
undesirables_. Even if no `report()` fired (because the callback dedup'd before reporting), the cache size is itself a signal that something matched
the watcher's predicate.

### 5. The absence of expected emissions

The inverse: if a watcher is _known_ to fire on a recurring overlay (e.g. a cookie banner that always appears for first-session users), and the run
report shows zero emissions for it, that's also a signal — either the overlay stopped appearing (good, but worth knowing) or the watcher broke
silently (per `analyse-watcher-flakiness §2`: swallowed callback exceptions).

## Procedure

### Step 1 — Inventory the watchers registered in this run

```bash
grep -rn "Watcher\[\|watchers=" src
```

For each watcher: name, callback, where attached. If the inventory is empty for the project, then this skill's output is also empty — surface that
explicitly: _"No watchers registered; no emissions possible."_

If watchers exist, list them; the inventory becomes the per-watcher lens for Steps 3–5.

### Step 2 — Pick the report + log + screenshot set

Per `pick-reports`, `pick-logs`, `pick-screenshots`: always mtime-sorted. Cross-reference run IDs across the three.

### Step 3 — Scan the screenshots for stray frames

Group screenshots by test (same approach as `analyse-screenshot-flakiness`). For each burst:

- Identify the failure-frame timestamps (correlate with the FAIL line in the log).
- Identify the step-frame timestamps (if per-step capture is on).
- **Any remaining frame** is a candidate watcher emission.

For each candidate, find the matching log line: same timestamp ±100ms, watcher-tagged source, `report()` content as the log message.

### Step 4 — Scan the log for watcher lines

Filter the log to watcher-sourced lines (use the watcher name tag from `analyse-watcher-flakiness`'s instrumentation if present, else heuristic
match). For each:

- Which watcher fired?
- On which test was it attached?
- What did the message say?
- Did it correspond to a screenshot (cross-reference back to Step 3)?

### Step 5 — Scan the report for non-status entries

Open the JSON / DOCX. For each test, look for `attachments`, `notes`, `watcher_reports`, or any field that isn't `status` / `name` / `duration`. The
exact field name depends on the report shape — read the schema once, then filter.

### Step 6 — Cross-check the expected vs observed firing pattern

For each known-fire watcher (one with a deterministic trigger):

- Were the expected emissions present? (Hits §1.)
- Were unexpected emissions present? (Real new findings.)
- Were emissions _absent_ when they should have appeared? (Hits §5 — possible silent watcher break; hand off to `analyse-watcher-flakiness`.)

### Step 7 — Surface the emissions list

```markdown
# Watcher-emission review — `<run id>` (<timestamp>)

## Watchers registered in this run

- `<name>` — callback `<path:line>`, attached to `<scenario(s)>`. Known trigger: `<expected behaviour>`.
- ... (or "none — no emissions possible")

## Emissions observed

### `<watcher name>` on `<test name>` (`<browser>`)

- Log line: `<file>:<line>` at `<timestamp>` — message: `<verbatim quote>`.
- Screenshot: `<file in <gitignored>/screenshots/>` (cross-referenced by timestamp).
- Test status: <PASS | FAIL — note both; emission stands either way>.
- **Reading (per Ocarina convention)**: the watcher reported, therefore something **undesirable** was observed: `<one-sentence interpretation>`.
- Cross-reference: matches `the gap inventory <entry-ref>` | new finding candidate.

(One block per emission.)

## Anomalies

### Expected emissions missing

- `<watcher name>` was expected to fire on `<test>` (known trigger `<…>`), did not. Possible causes:
  - The trigger condition didn't actually occur (good — verify in screenshots).
  - The watcher's callback broke silently (hand off to `analyse-watcher-flakiness §2`).

### Unexpected high-frequency emissions

- `<watcher name>` fired <N> times on `<test>` — normal range is <m>. Possible causes:
  - The undesirable condition got worse (real finding).
  - Watcher dedup (cache) collision (hand off to `analyse-watcher-flakiness §5`).

## Cross-references

- the gap inventory <entry-refs>.
- Diagnostic next motions: `analyse-watcher-flakiness` (for watcher-side concerns), `analyse-screenshot-flakiness` (for visual triage),
  `update-frd-and-tests` (if a recurring emission warrants a §9 gap entry).

## Open follow-ups

- <emission with ambiguous interpretation> — invoke `write-a-probe` to capture the DOM state at the emission timestamp.
- <missing-emission case> — re-run with `analyse-watcher-flakiness` instrumentation to confirm the watcher fires at all.

## Verdict

<one-line: <N> emissions, all explained / <K> new findings worth a probe / one watcher likely broken silently / no emissions, nothing material>.
```

### Step 8 — Stop. The user decides.

Each emission can resolve as:

- **File as gap** — recurring undesirable observed → the gap inventory entry via `update-frd-and-tests`.
- **Already explained** — emission matches an existing known-bug / environmental / browser entry → cross-reference, no new action.
- **Watcher-side concern** — emission looks like a watcher bug → `analyse-watcher-flakiness`.
- **DOM uncertainty** — interpretation unclear → `write-a-probe` for the moment in question.
- **Defer** — rare or low-impact; revisit if it recurs.

## Hard rules

- **Treat every watcher emission as a negative signal.** By Ocarina convention, watchers only report the undesirable. An emission is never "just
  noise".
- **Don't mistake an emission for a test failure.** The test may have PASSED; the emission is a _separate_ observation about the run's environment.
- **Don't mistake an emission for clutter in the screenshot folder.** A "stray" frame mtime-adjacent to a watcher log line is the watcher's
  contribution to the negative-signal record.
- **Absent expected emissions are also a signal.** A watcher that fires on a known trigger but didn't this run — verify whether the trigger really
  vanished or whether the watcher broke silently.
- **Always cross-reference log + screenshot + report entry.** A claimed emission with no log line is unverifiable.
- **Don't include attack-shape inputs in any follow-up probe.** Per `CLAUDE.md` → "Security testing is functional and static — never active".

## When to run this skill

- After every `review-report` pass — emissions are the axis that skill explicitly doesn't cover.
- When a screenshot folder has "more files than expected" for a run.
- When a watcher exists in the suite and the team wants to know what it has been silently catching.
- Before publishing a PR that touches watcher-instrumented scenarios — verify the watcher's emissions haven't changed shape unexpectedly.
- When the user says: "is anything weird in the report I should know about?" — the weird stuff is often the watcher emissions.

## What this skill does NOT do

- It does not audit the watcher's _correctness_ (whether it fires deterministically, whether the callback is racy). Use `analyse-watcher-flakiness`.
- It does not run multi-replay comparisons. Use `review-suite-stability`.
- It does not classify FAIL / SKIP incidents. Use `review-report`.
- It does not probe the DOM to confirm what the watcher saw. Use `write-a-probe` if the emission's interpretation is ambiguous.
- It does not file gap entries. Cross-references are recommended; entries are a follow-up via `update-frd-and-tests`.
- It does not modify any run artifact. Read-only.
