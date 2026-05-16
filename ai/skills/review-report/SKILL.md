---
name: review-report
description:
  '**Read an Ocarina run report and the matching logs as a careful reviewer would** — surface every FAIL and every SKIP, then **classify each by
  reason** because the reading is different in each case. A FAIL in the test body reads differently from a FAIL in setup; a SKIP because the smoke
  gate cut the main campaign reads differently from a SKIP because the test was statically marked `skipped=True`; a SKIP because setup raised reads
  differently from either. The skill walks the report (JSON + DOCX from `.reports/`, picked per `pick-reports`), cross-references each FAIL / SKIP to
  its log line (per `pick-logs`) and screenshot burst (per `pick-screenshots`), and produces a **classified incident list** with the right diagnostic
  next step for each class. Use whenever the user asks to read a report, audit a CI run, triage failures and skips, prepare a post-run summary, or
  onboard a contributor to what the suite produced today.'
---

# Review a run report — FAIL is not FAIL, SKIP is not SKIP

A reading skill. The report file alone is not the artifact you reason from — it's the _index_. Each FAIL has a reason in the logs; each SKIP has a
reason in the cycle's smoke / setup / static config. Without the classification, an "8 failures, 12 skips" headline is just noise; with it, you get "3
real defect-suspect FAILs, 5 transport FLAKEs, 10 smoke-gate-blocked SKIPs (expected when smoke is red), 2 setup-error SKIPs (real)".

This skill complements `pick-reports` / `pick-logs` / `pick-screenshots` (which choose _which_ files to read) and `review-suite-stability` (which runs
multiple replays to classify _categories_ of test). This one reads **a single run** carefully.

## The classification axes

### FAIL classes (three primary)

1. **Test-body FAIL** — the assertion in the test chain or a step inside `drive_page` raised. The log shows the exception and the line in the scenario
   / POM. This is the "default" FAIL and the only one most readers expect.
2. **Setup FAIL** — the test never reached the body; `setup` raised. Per Ocarina's scenario contract (see
   `<gitignored>/ocarina/.../custom_types/scenario.py`): if setup raises, the test chain is **skipped**, teardown still runs, and the test is marked
   accordingly. **Read carefully**: this can present as a SKIP in the report (not a FAIL) depending on the framework's encoding. Confirm by reading
   the log.
3. **Teardown FAIL** — the test body passed (or failed for a body reason), but teardown itself raised. Often a leaked cookie, an unclosed alert, a
   driver crash on logout. Reads differently from body FAILs because the _failure didn't cause the test_; the failure happened _cleaning up_ the test.

### SKIP classes (four primary)

1. **Static SKIP** — the test was authored with `skipped=True`. Intentional, no investigation needed. Confirm in the source
   (`grep -n "skipped=True"`).
2. **Smoke-gate SKIP** — a smoke test failed and the main campaigns were cut by the cycle's smoke gate (see
   `<gitignored>/ocarina/.../dsl/testing/oc_test_cycle.py`: _"Main sequences are skipped if any smoke test failed."_). The skipped tests are _fine_;
   the real signal is the smoke failure that triggered the cut.
3. **Setup-error SKIP** — the test's `setup` raised, so the body was skipped (the Ocarina contract above). The test wasn't _deliberately_ skipped; it
   was **forced** to skip by a failed precondition. Reads as a real investigation target — same gravity as a FAIL.
4. **Cycle-policy SKIP** — the cycle / campaign / suite policy excluded the test from this run (a tag filter, a `--workers` partition, an exit-early
   policy). Reads as "expected for this run shape, not a defect".

Two SKIPs with identical encoding in the JSON can have wildly different meaning; the _only_ way to tell them apart is the log + the source.

### Cross-axis: did retries (test lives) get used?

For every FAIL, check the log for retries. A test that died on its first life is a different signal from one that died after exhausting all lives —
the second is closer to a chronic flake or a real defect (per `analyse-flakiness`).

## Procedure

### Step 1 — Pick the report set

Per `pick-reports`: **mtime, not name**.

```bash
ls -dt .reports/docx/* | head -1   # latest DOCX run folder
ls -t  .reports/json/*.json | head -1   # latest JSON
```

For a single-run review: the latest pair. For a "last K runs" comparison: the top K.

### Step 2 — Pick the matching log root

Per `pick-logs`: latest `.ocarina_logs_<id>/` by mtime, cross-checked against the report's run id.

```bash
ls -dt .ocarina_logs_* | head -1
```

### Step 3 — Read the JSON; build the raw table

For each test in the report:

| Test | Browser | Status | Worker | Lives used | Duration |

The JSON encodes status as one of `Ok` / `Fail` / `None` (per `<gitignored>/ocarina/.../custom_types/oc_test_layers.py`: _"Single test execution
result: Ok (passed), Fail (failed), or None (skipped)."_).

Don't classify yet. Just enumerate.

### Step 4 — Classify each FAIL

For each FAIL row, open the log around the test's start / end. Identify:

- **Where the exception was raised** — inside the test chain, inside `setup`, inside `teardown`?
- **Exception class** — `WebDriverException`, `TimeoutException`, `AssertionError`, a project-local exception (`BackForwardCacheExposureError`).
- **Lives used** — 1 (died fast), or all (exhausted retries).

Map to:

- Body FAIL / Setup FAIL / Teardown FAIL.

If the exception class matches a known artifact (`§A-ENV-1`, `§A-ENV-2`, `§B-BROWSER-1`), tag the cross-reference now.

### Step 5 — Classify each SKIP

For each SKIP row, the JSON status alone is insufficient. Decide by checking, in order:

1. **Source check** — `grep -n "name=\"<test name>\"" src/tests/scenarios` for `skipped=True`. If found → **Static SKIP**. Done.
2. **Smoke check** — is there any FAIL with `is_smoke=True` (or the equivalent campaign-level tag) in this run? If yes, and the SKIP test belongs to a
   main (non-smoke) campaign → **Smoke-gate SKIP**. Done.
3. **Log check** — search the log for the test's `setup` entries. Did setup raise? If yes → **Setup-error SKIP**. Done.
4. **Otherwise** — **Cycle-policy SKIP** (or "unclassified — investigate"). Log the test name as needing manual triage.

A Setup-error SKIP is **not** "low-priority because skipped" — it's a forced skip from a real precondition failure, and the diagnostic is identical to
a Setup FAIL.

### Step 6 — For each incident, attach the screenshot burst

Per `pick-screenshots`: the burst tied to the test's failure / setup-error timestamp. A FAIL with no screenshot burst is suspicious — either the
take-screenshot hook itself flaked (boundary issue, see `analyse-fixture-flakiness`) or the test died before any capture was triggered.

Add the burst paths to the incident.

### Step 7 — Surface the classified incident list

Use this exact template:

```markdown
# Report review — `<run id>` (<timestamp>)

## Run shape

- Browsers: <list>.
- Workers: <count>.
- Smoke gate: <PASS | FAIL — list which smoke test(s) failed>.

## Headline (with classification — NOT raw counts)

- Test-body FAILs needing investigation: <N>
- Setup FAILs (real preconditions broken): <N>
- Teardown FAILs (test passed body, but cleanup broke): <N>
- Setup-error SKIPs (forced skip, treat as Setup FAIL): <N>
- Smoke-gate SKIPs (expected — smoke cut the main campaigns): <N>
- Static SKIPs (intentional, `skipped=True`): <N>
- Cycle-policy SKIPs (expected for this run shape): <N>

Raw JSON totals would say "<X> failures, <Y> skipped"; the real reading is above.

## Test-body FAILs

### `<test name>` on `<browser>`

- Exception: `<class>` at `<scenario/POM file>:<line>` (log: line `<N>` in `<log file>`).
- Lives used: <1 | all> of <N>.
- Screenshot burst: `<file>`, `<file>` (in `<gitignored>/screenshots/`).
- Cross-reference: matches `the gap inventory <entry-ref>` | new candidate.
- Diagnostic next step: <re-run in isolation | `write-a-probe` to isolate | `analyse-flakiness` on the transient classification | already-explained,
  no action>.

(One block per FAIL.)

## Setup FAILs (and Setup-error SKIPs — read together)

### `<test name>` on `<browser>` (encoded as <FAIL | SKIP> in JSON)

- Setup step that raised: `<step>` at `<file>:<line>`.
- Exception: `<class>`.
- Screenshot burst: <if any — setup screenshots may not exist>.
- Cross-reference: <…>.
- Diagnostic next step: <`analyse-fixture-flakiness` is the matching motion | already-explained>.

## Teardown FAILs

### `<test name>` on `<browser>`

- Body status: <PASSED | FAILED for separate reason — note both>.
- Teardown step that raised: <…>.
- Risk of cross-test contamination: <high | low — based on whether logout / cookie clear ran>.
- Diagnostic next step: <`analyse-fixture-flakiness`>.

## Smoke-gate SKIPs

- Smoke test(s) that triggered the gate: `<test names>` — see Test-body FAILs section above.
- Main campaigns cut: <list> (<N> tests).
- **Reading**: these are expected, not failures. The investigation is the smoke FAIL above.

## Static SKIPs

- `<test name>` — authored `skipped=True` in `<file>:<line>`. Reason: <if commented; otherwise "no comment">.

## Cycle-policy SKIPs

- <test names> — filtered by <tag / partition / policy>.

## Unclassified

- (Any incident the procedure couldn't classify. Manual triage needed.)

## Cross-references

- the gap inventory <entry-refs>.
- Diagnostic skills suggested: <`analyse-flakiness`, `analyse-fixture-flakiness`, `analyse-screenshot-flakiness`, `write-a-probe`>.

## Verdict

<one-line: this run looks healthy / N defect candidates worth a probe / smoke is broken and that's the only signal / nothing material>.
```

Print the list. Don't write to a file unless the user asks.

### Step 8 — Stop. The user picks the next motion.

Each incident class maps to a different next motion:

- **Test-body FAIL** → `write-a-probe`, `analyse-flakiness`, or `update-frd-and-tests` if it's a real defect.
- **Setup FAIL / Setup-error SKIP** → `analyse-fixture-flakiness`.
- **Teardown FAIL** → `analyse-fixture-flakiness`.
- **Smoke-gate SKIP** → no action on the skip itself; investigate the smoke FAIL that triggered it.
- **Static SKIP** → consider whether the `skipped=True` is still warranted; if the underlying gap is resolved, run `update-frd-and-tests`.
- **Cycle-policy SKIP** → no action.
- **Unclassified** → manual triage; in the next pass the rule that catches it should be added to this skill.

## Hard rules

- **A raw count is not the reading.** "8 failures" is meaningless; "3 body FAILs, 2 setup FAILs, 3 teardown FAILs" is the reading.
- **A SKIP without classification is not a SKIP — it's an open question.** The four SKIP classes have entirely different urgency profiles.
- **Setup-error SKIPs are not low-priority.** They're forced skips from a real precondition failure. Read with the same gravity as a Setup FAIL.
- **Smoke-gate SKIPs are not failures.** They're the _consequence_ of the smoke FAIL. Don't double-count.
- **Always cross-reference to the log line.** A FAIL without a log line is unverifiable; a screenshot without a log line is unprovenanced.
- **Always cross-reference to the gap inventory.** Many incidents are already-explained; not noting that is duplicate investigation.
- **Mtime-sort everything.** Reports, logs, screenshots. Per `pick-reports` / `pick-logs` / `pick-screenshots`.

## When to run this skill

- After every CI run worth reading (CI summary or local).
- Before a `pr-report`: the report review feeds the test plan / risk section.
- After a `review-suite-stability` pass: the per-run classified incidents are the unit input for the multi-run stability verdict.
- When triaging a "the suite is red" alert — read the report first, dispatch to the right diagnostic skill second.
- Onboarding: walking a contributor through one classified report builds the mental model faster than reading the docs.

## What this skill does NOT do

- It does not pick the report / log / screenshot files. Use `pick-reports` / `pick-logs` / `pick-screenshots` first.
- It does not run multi-replay analysis. Use `review-suite-stability` for that.
- It does not investigate root causes. It surfaces incidents with their classification and the _suggested_ next motion; the next motion is a separate
  skill invocation.
- It does not update the gap inventory or the FRD. Cross-references are recommended; entries are a follow-up via `update-frd-and-tests`.
- It does not modify the report files or the logs. Read-only.
