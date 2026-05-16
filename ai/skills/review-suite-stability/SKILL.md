---
name: review-suite-stability
description:
  Run the e2e cycle multiple times across the browser matrix (Firefox + Chrome) and verify the **per-test outcome** stays consistent and matches the
  documented expected categories — pass-everywhere tests staying green, the documented intentional-fail gap tests staying red on both browsers, the
  documented Chrome BFcache reds staying red on Chrome / green on Firefox, and **nothing else flapping**. Locally or via `gh workflow run`; default 3
  replays per browser. Reports per-test stability (`PASSED 3/3`, `FAILED 3/3 (intentional gap)`, `FLAKE — PASSED 2/3 / FAILED 1/3`) — never a total
  count, because `--workers` clones inflate any total. Use whenever the user asks to verify suite determinism, run a release-baseline check, hunt for
  flaky tests, audit before cutting a release, or confirm a refactor didn't introduce non-determinism.
---

# Review — suite stability across replays and browsers

Runs the e2e cycle **N times per browser**, parses every per-run JSON result, builds a per-test status matrix, and surfaces deviations from the
documented expected outcome. The point is **per-test consistency**, not aggregate counts: `--workers 3` clones inflate any total, and a stable suite
is one where every test's _outcome_ matches its documented category across every replay.

Defaults: 3 replays per browser, browsers = Firefox + Chrome, source of truth = `CURA_TEST_STRATEGY.md` §7. Locally or via GA dispatch; the procedure
is the same.

The audit does not edit tests, does not silence flakes, does not retry-until-green. It runs, it reads, it reports.

## Expected outcome categories (the load-bearing dataset — sourced from the strategy doc)

Read these from `CURA_TEST_STRATEGY.md` §7 each run — do not hardcode them in the skill. The categories rotate as the suite evolves. As of the last
update of this skill, the three categories are:

| Category                                             | Tests                                                                                                                                                                                                                                                                                                                                                   | Expected on Firefox | Expected on Chrome |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | ------------------ |
| **Pass everywhere**                                  | All tests not listed in the other categories                                                                                                                                                                                                                                                                                                            | PASS, every replay  | PASS, every replay |
| **Intentional gap fails — red on both, by design**   | `Appointment - Past date booking accepted` (§9.7); `Appointment - Server accepts empty date when client bypass applied` (§9.1); `Appointments - Duplicate booking (same facility, date, program)` (§9.6); `Appointments - Overlapping appointments (same date, different facilities)` (§9.6); `Journey - History ordered most-recent date first` (§9.8) | FAIL, every replay  | FAIL, every replay |
| **Chrome BFcache reds — red Chrome / green Firefox** | `Logout - Back-button does not restore authenticated history view`; `Logout - Session holds under back-forward stress (3 cycles)`                                                                                                                                                                                                                       | PASS, every replay  | FAIL, every replay |

If the strategy doc updates these categories (a new gap landed, a CURA fix flipped one to green), the skill picks them up on the next run because it
reads the doc — not the skill.

The skill's classification of a per-test outcome:

- **EXPECTED PASS** — pass-everywhere category, all replays pass on that browser.
- **EXPECTED FAIL** — intentional-gap test on both browsers, all replays fail; or Chrome BFcache test on Chrome.
- **EXPECTED CROSS-BROWSER PASS** — Chrome BFcache test on Firefox, all replays pass.
- **FLAKE** — same browser, mixed PASS/FAIL across replays.
- **REGRESSION** — pass-everywhere category, ≥ 1 FAIL on either browser.
- **SURPRISE GREEN** — intentional-fail or Chrome BFcache test that unexpectedly passed on its expected-red browser. May mean CURA fixed it; may mean
  §A-ENV-1 contention false-passed it. Verify before celebrating.
- **SURPRISE RED ON FIREFOX** — Chrome BFcache test that failed on Firefox. The BFcache exposure is supposed to be Chrome-only.

`[COPY N]`-suffixed tests are clones (`--workers 3` saturation); treat each copy as the same test (their outcomes should match the base test's
category).

## Procedure

### 1. Resolve replays and browsers

Defaults: `N=3`, browsers = `firefox` `chrome`. If the user wants more replays (release-readiness pushes for 5+) or one browser only, take the
override.

### 2. Read the expected categories from the strategy doc

```bash
sed -n '/^## 7. /,/^## /p' CURA_TEST_STRATEGY.md
```

Parse the bullets under "Intentional gap fails" and "Expected cross-browser reds on chrome" for the test names. Anything not listed lands in **Pass
everywhere**.

### 3. Run the replays

**Local** (default — cheaper, faster after the password-modal fix):

```bash
# per-browser, per-replay
cd the project root
mkdir -p .reports/stability/<run-id>
for browser in firefox chrome; do
  for i in 1..N; do
    ./.venv/bin/python -u -m src.main \
      --driver-path <driver-for-browser> \
      --browser $browser \
      --workers 3 \
      --wait-timeout 15 \
      --logger terminal+file
    # capture the JSON result before the next run overwrites
    cp .reports/json/<latest>.json .reports/stability/<run-id>/$browser-$i.json
  done
done
```

**Via GA** (canonical reference per CLAUDE.md):

```bash
# dispatch N times
for i in 1..N; do
  gh workflow run e2e.yml --ref main
done
# wait for completion, then fetch results
gh run list --workflow=e2e.yml --limit $((N * 2))   # N runs × 2 jobs
# extract JSON-result artifacts from each run's "reports-<browser>" artifact
```

The skill does not block for completion; if the user dispatches GA runs, wait for them to land (the runtime told us ~3 min per run with the current
fixes) and then parse.

### 4. Parse each per-run JSON

For each `.reports/stability/<run-id>/$browser-$i.json`, walk the nested results and produce `{test_name: status}`. Status is one of `success` /
`fail`. Strip the `[COPY N]` prefix when bucketing (a copy's outcome belongs to the underlying test).

### 5. Build the per-test matrix

For each test, build a row across replays per browser:

| Test                                     | FF-1 | FF-2 | FF-3 | CH-1 | CH-2 | CH-3 | Category             | Verdict                              |
| ---------------------------------------- | ---- | ---- | ---- | ---- | ---- | ---- | -------------------- | ------------------------------------ |
| Valid Login - John Doe                   | P    | P    | P    | P    | P    | P    | Pass everywhere      | EXPECTED PASS ✓                      |
| Appointment - Past date booking accepted | F    | F    | F    | F    | F    | F    | Intentional gap fail | EXPECTED FAIL ✓                      |
| Logout - Back-button does not restore …  | P    | P    | P    | F    | F    | F    | Chrome BFcache red   | EXPECTED CROSS-BROWSER PASS / FAIL ✓ |
| (hypothetical) Journey - Book and Verify | P    | P    | F    | P    | P    | P    | Pass everywhere      | FLAKE                                |

### 6. Classify each row per the table above

Apply the rules deterministically — no judgement here; the categories are read from the doc.

### 7. Report

Use this exact template:

```markdown
# Suite stability — <N> replays × Firefox/Chrome on <main HEAD | branch | local snapshot>

## Categories (from `CURA_TEST_STRATEGY.md` §7)

- Pass everywhere: <count> tests
- Intentional gap fails: <list of names>
- Chrome BFcache reds: <list of names>

## Results

### Stable

- All `Pass everywhere` tests passed <N>/<N> on both browsers.
- All intentional gap fails failed <N>/<N> on both browsers.
- All Chrome BFcache reds: passed <N>/<N> on Firefox; failed <N>/<N> on Chrome.

### Flakes

- <test name> — Firefox: P/P/F; Chrome: P/P/P. Investigate.
- <test name> — Chrome: P/F/P. Investigate.

### Regressions (Pass-everywhere tests that failed)

- <test name> — Firefox: P/P/F. Trace the failing run: `<run-id>`.

### Surprise greens

- <test name> (intentional gap §9.X) — Chrome: P/F/F. One run passed unexpectedly. Likely §A-ENV-1 transport flake (per `IDENTIFIED_GAPS.md` §A-ENV-1
  — rapid-POST drop under `--workers 3` mimics rejection). Re-run to confirm; do **not** flip the gap test to green without verification (see the
  `empiricism` skill).

### Surprise reds on Firefox

- <test name> (Chrome BFcache red) — Firefox: F. The BFcache exposure is supposed to be Chrome-only; Firefox failing is new. Investigate.

## Verdict

<stable / flakes detected / regressions detected — pick one and lead with it>
```

Print the report; do not write it to a file unless the user asks.

### 8. Stop. The user decides.

Do not flip tests. Do not silence flakes by adding `transient_errors` entries. Do not "fix" surprise greens by editing the gap tests. Hand the report
over.

## Things this skill does NOT count

Per `CLAUDE.md` and `CURA_TEST_STRATEGY.md` §7:

- **Total pass/fail across the suite.** Meaningless under `--workers 3` clone inflation; the categories are what matter.
- **Per-run duration aggregates.** Useful elsewhere (see `IDENTIFIED_GAPS.md` §A-ENV-2's note on the chrome-job time drop), not relevant to stability.
- **The `[COPY N]` clones themselves**, except as confirmation: they should match the base test.

## Investigating a flake

If the audit surfaces a flake, the next moves (none of which this skill does):

1. Read the per-run logs / screenshots for the failing replays. The autoscreen burst on failure captures four screenshots — use them.
2. Check `IDENTIFIED_GAPS.md` §A-ENV-1 (shared-dyno contention) — rapid 2nd-in-a-row POSTs on `--workers 3` can flake.
3. Check whether the failing replay coincided with a Heroku cold start (the first request after dyno sleep is slow).
4. If neither, write a probe per the `empiricism` skill.

The fix path for a real flake is in CLAUDE.md → "Verify SUT behaviour" and "A probe must exercise the exact target" — not in this audit.

## When to run this skill

- Release readiness — "is the suite deterministic on `main` HEAD?". The release-baseline check.
- After a refactor — confirm nothing started to flap.
- When a single GA run looks suspicious (one surprise green) — replay to disambiguate flake from genuine fix.
- Before promising a third party that the matrix is green.

## What this skill does NOT do

- It does not run the suite once. One replay can't distinguish stable from flaky.
- It does not edit tests, `transient_errors`, or driver options to make a flake go away.
- It does not adjust the documented expected outcome — that's the strategy doc's job, edited by hand with intent.
- It does not estimate "flake rate" as a percentage. Per-test, per-browser, P/F counts only — they're more honest.
