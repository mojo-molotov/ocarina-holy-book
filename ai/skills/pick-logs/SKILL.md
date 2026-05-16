---
name: pick-logs
description: Locate and surface logs after a cycle run — sorted strictly by **directory modification time**, never by the random suffix in the directory name. The log root location is determined by Ocarina's `get_default_log_dir()` (used by `main.py`'s `bootstrap(...)` call), which typically produces a `.ocarina_logs_<id>/` directory at the cwd — but the skill **reads `main.py` to confirm the configured log dir** before guessing, and falls back to a filesystem walk if the wiring is opaque. Each run creates a fresh log-dir root; the latest run is whichever root has the most recent mtime. Use whenever the user asks to see the latest log, look at a failing test's log, find which log mentions a specific screenshot, or read the act-by-act trail of a test. Same discipline as `pick-screenshots`: sort by date, never by name. Surface a listing; the user picks which log to open.
---

# Pick logs — by mtime, never by directory name

Same rule as `pick-screenshots`. Each cycle run produces a directory tree like:

```
<configured-logs-root>/
  CURA E2E/
    <Campaign name>/
      <Suite name>/
        <Test name>.log
        [COPY 1] <Test name>.log     # if --workers N produced clones
        ...
```

The root carries a random suffix; **log directories do not sort by recency alphabetically**. Always use mtime. Anything else picks the wrong run.

## Locate the log root

### Step 1 — Read the bootstrap call

The log dir is determined by `get_default_log_dir()` from `ocarina.opinionated.loggers.create_matching_logger`, called inside `main.py` or whichever
file invokes `bootstrap(...)`. Look for it:

```bash
grep -rn "get_default_log_dir\|bootstrap(" src --include="*.py"
```

In the default Ocarina setup this resolves to `.ocarina_logs_<id>/` at the cwd. If the project customises it (an explicit `logger` config, an env
override), follow the trail.

### Step 2 — Fall back to filesystem if config is opaque

```bash
find . -maxdepth 3 -type d -name ".ocarina_logs_*" 2>/dev/null
```

### Step 3 — Pick the latest by mtime

Substitute the resolved path for `<logs-parent>` below.

```bash
latest=$(ls -dt <logs-parent>/.ocarina_logs_* 2>/dev/null | head -1)
echo "$latest"
```

If nothing matches, no run has produced logs yet — say so and stop. If multiple recent roots exist (two runs back-to-back), surface both:
`ls -dt ... | head -3` and let the user pick which run they meant.

## List the per-test logs under one root

```bash
find "$latest" -name "*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -<N>
# macOS:
find "$latest" -name "*.log" -type f -exec stat -f '%m %N' {} + | sort -rn | head -<N>
```

Default `N = 20` — enough to surface every test in a small-to-medium cycle. Override on request.

Strip the `[COPY N] ` prefix when bucketing for status: a copy belongs to the same test as the base; their outcomes should match (per
`review-suite-stability`).

## Filter to failures only

A failing test's log contains:

- A line starting with `🛑` (the failure marker from Ocarina's logger).
- A Python traceback (`Traceback (most recent call last):`).
- The autoscreen burst of four screenshot lines in quick succession (one per `FAIL_<uuid>_<n>.png`).

```bash
# all failing test logs in the latest root
grep -rl "🛑" "$latest" --include="*.log"
# or grep for Traceback if the icon isn't reliable in your terminal
grep -rl "^Traceback " "$latest" --include="*.log"
```

## Cross-reference from a screenshot to its log

Given a screenshot basename (`PASS_<uuid>.png` or `FAIL_<uuid>_<n>.png`), find the log line that names it:

```bash
grep -rln "<basename>" <logs-parent>/.ocarina_logs_* --include="*.log" | head -1
```

That gives you the test log; opening it shows the surrounding success/failure messages, the chronology, and any traceback. The pair
`pick-screenshots → pick-logs` is the standard motion for investigating a failure: see the shots, then read the trail.

## Surface — structured table

Output:

```markdown
# Logs — `<latest log root>` (top N by mtime)

| #   | Test                                                             | Status | Modified            | Size   | Path        |
| --- | ---------------------------------------------------------------- | ------ | ------------------- | ------ | ----------- |
| 1   | Logout - Session Cleared (via sidebar link)                      | PASS   | 2026-05-15 18:42:30 | 1.2 KB | <full path> |
| 2   | Logout - Back-button does not restore authenticated history view | FAIL   | 2026-05-15 18:41:53 | 6.8 KB | <full path> |
| 3   | (COPY 1 of above)                                                | FAIL   | 2026-05-15 18:41:54 | 6.5 KB | <full path> |
| 4   | Logout - Server-side session invalidation enforced on reload     | PASS   | 2026-05-15 18:42:02 | 1.4 KB | <full path> |
| ... | ...                                                              | ...    | ...                 | ...    | ...         |
```

Always include:

- **Test** — the test name; mark `(COPY N of above)` for the `--workers` clones grouped under the base.
- **Status** — PASS / FAIL inferred from the log content (presence of `🛑` or `Traceback`).
- **Modified** — mtime; this is the sort key.
- **Size** — the failing logs tend to be larger (the traceback adds bytes); useful as a glance signal.
- **Path** — absolute, so the user can copy-paste into a Read call.

## Opening a log

Reading a log is a separate motion (a `Read` call on the full path). The skill produces the listing; the user picks which to open.

A common pattern when investigating a failure: open the failing test's log (full), then open the autoscreen-burst screenshots it cites (via
`pick-screenshots`'s cross-reference). The log gives chronology + cause; the shots give visual state.

## Stop. The user decides what to open.

Like `pick-screenshots`, this is a navigation skill. The user reads the surfaced log files themselves.

## Examples

### Right after a run

```bash
ls -dt <logs-parent>/.ocarina_logs_* | head -1
# → <logs-parent>/.ocarina_logs_<id>
```

Then list the 20 most recent `.log` files under that root, with `PASS`/`FAIL` flags inferred from content.

### Failing-test-only listing

```bash
grep -rl "🛑" "$latest" --include="*.log"
```

A short list — only the tests that failed. For a fully expected run (5 intentional fails + 2 BFcache reds on Chrome), expect 7 entries. Anything else
is a regression candidate (see `review-suite-stability`).

### Cross-reference from a screenshot

The user is looking at `FAIL_837f3b8c_1.png` from `pick-screenshots`. They want the log trail:

```bash
grep -rln "FAIL_837f3b8c_1.png" <logs-parent>/.ocarina_logs_* --include="*.log"
# → .../Authentication/Session management/Logout - Back-button does not restore authenticated history view.log
```

Then open that log to read the chronology — the success messages leading up to the failure, the failure message itself, the traceback, the burst of
four screenshot citations.

### Sorting trap — what NOT to do

```bash
# wrong — UUIDs sort lexicographically, not by recency
ls <logs-parent>/.ocarina_logs_* | head -1
```

Returns _whichever directory sorts first alphabetically_, not the most recent run. Same rule as for screenshots: filenames/dirnames with random
suffixes do not encode time.

## When to run this skill

- The user asks: "show me the latest log", "what did test X log?", "which tests failed in the last run?", "what's the trail for that screenshot?"
- After a local cycle run, before reviewing.
- When `review-suite-stability` surfaces a flake or surprise green/red — the failing-test log is the next read.
- Companion to `pick-screenshots` when investigating a failure visually + textually.

## What this skill does NOT do

- It does not sort by filename. Ever.
- It does not delete or move log files.
- It does not open logs itself — the listing is the deliverable; opening is a follow-up `Read` call.
- It does not parse semantic structure beyond PASS/FAIL inference — extracting "what step failed" / "what was the assertion" / "what was the
  traceback" is the user's read, not the skill's parse.
- It does not aggregate stats (count of PASS/FAIL) — that's `review-suite-stability` working from the JSON report, which is more reliable than parsing
  logs.
