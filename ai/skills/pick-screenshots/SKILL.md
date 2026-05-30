---
name: pick-screenshots
description:
  List and surface the N most recent screenshots after a cycle run — sorted strictly by **file modification time**, never by filename. Filenames carry
  random UUID suffixes (`PASS_<uuid>.png`, `FAIL_<uuid>_<n>.png`) that don't sort meaningfully by recency, so any naive alphabetical/`ls` listing
  returns the wrong files. The screenshot directory is a flat **heap** — every run dumps its shots into the same folder with no run boundary, so mtime
  alone tells you recency but not which run a shot belongs to or what it means. The only thing that truly contextualises a screenshot is a **log line
  that names it**. So this skill always inspects for **fresh logs** first: it locates the latest `.ocarina_logs_*` root by mtime, then cross-references
  every picked screenshot against it — a shot named in the fresh logs belongs to the latest run and carries its test/step context; a shot with no
  fresh-log hit is from an older run or orphaned, and is surfaced as such. The screenshot directory isn't a fixed convention — it's determined by the
  **test code's** screenshot handler factories (typically configured in `src/lib/ext/ocarina/adapters/<adapter>/logs.py` — `selenium` or `playwright` — or similar, with calls like
  `create_log_success_and_take_screenshot(...)`). The skill **reads the screenshot factory wiring** to find the configured path, then falls back to a
  filesystem walk. Use whenever the user asks to see the latest screenshots, look at the fail burst from a recent run, inspect a passing test visually,
  or audit the report-quality after a screenshot-rule change.
---

# Pick recent screenshots — by mtime, never by filename

After a cycle run, screenshots accumulate in a directory the project's test code chose:

- **PASS shots** — one per `log_and_screenshot(...)` success → `PASS_<uuid>.png`.
- **FAIL bursts** — four shots per failed `act` (the `autoscreen_on_fail=True` burst on the `TestSuite` adapter) → `FAIL_<uuid>_1.png` …
  `FAIL_<uuid>_4.png`.

**The UUIDs are random.** They do not sort by recency. A naive `ls` listing returns the alphabetically-first N files, which is meaningless. **Always
sort by file modification time** when picking "the latest N" — `ls -t`, `find -newer`, or `os.path.getmtime` in Python. Anything else is wrong.

## Locate the screenshots dir

### Step 1 — Read the screenshot factory wiring

The path comes from the project's screenshot handler factory (typically `create_log_success_and_take_screenshot` or similar). Find where it's defined:

```bash
grep -rn "take_screenshot\|create_log_success_and_take_screenshot\|screenshot" src/lib --include="*.py"
# Plus the call sites that bind it:
grep -rn "log_and_screenshot\|autoscreen_on_fail" src --include="*.py"
```

Open the factory's definition; the destination directory is usually a `Path(...)` literal or a configurable parameter passed at bind time. Read the
actual value.

### Step 2 — Fall back to filesystem if the wiring doesn't make it obvious

```bash
# Look for any directory holding screenshot-shaped filenames
find . -maxdepth 3 -type d 2>/dev/null \
  | while read d; do
      [ -n "$(find "$d" -maxdepth 1 -name 'PASS_*.png' -o -name 'FAIL_*.png' 2>/dev/null | head -1)" ] && echo "$d"
    done
```

The hit (typically one) is the screenshots root. If empty, no run has produced shots yet — say so and stop.

## Inspect for fresh logs — the heap has no run boundaries

The screenshot directory is a **flat heap**. Every cycle run dumps `PASS_*` / `FAIL_*` shots straight into it; nothing in the directory marks where
one run ends and the next begins. mtime sorts the heap by recency, but recency is not run membership — the newest N files can straddle two runs, and a
shot's filename tells you nothing about which test or step produced it.

**The logs are what segment the heap.** Each run writes a fresh `.ocarina_logs_<id>/` tree, and every screenshot is named in exactly one log line
(`… — Screenshot: /…/PASS_<uuid>.png`). So before picking, locate the latest log root — the same motion as `pick-logs`:

```bash
# Read main.py's bootstrap call for the configured log dir (see pick-logs), then:
latest_logs=$(ls -dt <logs-parent>/.ocarina_logs_* 2>/dev/null | head -1)
echo "$latest_logs"   # → the fresh run's log root
```

If log-root resolution is non-trivial, defer to `pick-logs` — it owns that location step. The fresh log root's mtime is the **boundary**: shots
modified at or after it are candidates for "this run"; anything older is heap residue from earlier runs.

If there is **no** log root at all (a `--logger mute` run, or logs were cleaned), say so — the heap then has no context source, and every picked shot
is surfaced **(no log)**. Picking still works; it just can't be contextualised.

## Pick the N most recent — strictly by mtime

Default `N = 12` (enough to see one fail burst + 8 PASS frames of context, or about three drive_pages' worth of a passing scenario). Override on
request. Substitute the resolved path for `<screenshots-dir>` below.

```bash
ls -t <screenshots-dir>/*.png 2>/dev/null | head -N
# or, with mtime for the table (macOS):
stat -f '%Sm %N' -t '%Y-%m-%d %H:%M:%S' <screenshots-dir>/*.png 2>/dev/null | sort -r | head -N
# Linux:
find <screenshots-dir> -name "*.png" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -N
```

## Cross-reference each screenshot to its log line

Use the fresh log root resolved above (`$latest_logs`). The Ocarina log writes a line per shot:

```
[UTC_DATE::…] ℹ️  <SUT-NAME> E2E/Authentication/Session management/Logout - Session Cleared (via sidebar link) — Screenshot: /…/PASS_<uuid>.png
```

The line carries the test path (campaign / suite / test name) and the absolute path of the file. Grep the fresh log root for each picked shot:

```bash
grep -rh "PASS_<uuid>.png" "$latest_logs"
```

Two outcomes, and both are findings:

- **Hit in the fresh logs** → the shot belongs to the latest run. Its test/step context comes from the matched line; carry it into the table.
- **No hit in the fresh logs** → the shot is _not_ from the latest run, however recent its mtime looks. Widen across all `.ocarina_logs_*` roots to
  find which earlier run names it (`grep -rln "<basename>" <logs-parent>/.ocarina_logs_*`); mark the row **(earlier run)**. If no root names it at
  all, mark it **(no log)** — orphaned, possibly a probe or a manual click.

**This cross-reference is the point of the skill, not a footnote.** Because the directory is a heap, "the N newest files by mtime" is not "the last
run's N screenshots" — a slow earlier run, a probe, or an interleaved manual shot can land a stale file inside the mtime window. The fresh-log check
is what tells the user which rows are actually the run they asked about.

## Identify fail bursts

`FAIL_<uuid>_<n>.png` files (with `_1`, `_2`, `_3`, `_4` suffixes that share a UUID) belong to **one act failure**. When listing, group the four shots
together — they are one event, not four separate findings.

## Surface — structured table

Output:

```markdown
# Latest screenshots — `<dir>` (top N by mtime)

| #   | Modified               | Type       | File                 | Test                                                             | Step (success / failure log line)    |
| --- | ---------------------- | ---------- | -------------------- | ---------------------------------------------------------------- | ------------------------------------ |
| 1   | 2026-05-15 18:42:30    | PASS       | PASS_a1b2c3.png      | Logout - Session Cleared (via sidebar link)                      | Homepage displayed — session cleared |
| 2   | 2026-05-15 18:42:28    | PASS       | PASS_b2c3d4.png      | Logout - Session Cleared (via sidebar link)                      | Logged out                           |
| 3-6 | 2026-05-15 18:41:50–53 | FAIL burst | FAIL_e5f6a7_1..4.png | Logout - Back-button does not restore authenticated history view | (failure act — autoscreen burst)     |
| 7   | 2026-05-15 18:41:48    | PASS       | PASS_c4d5e6.png      | Logout - Back-button does not restore authenticated history view | Navigated back via browser history   |
| ... | ...                    | ...        | ...                  | ...                                                              | ...                                  |
```

Always include:

- **Modified** — the mtime. This is what made the file land in this listing.
- **Type** — `PASS` or `FAIL burst` (group the four together).
- **File** — basename (the UUID is fine; the user doesn't need the full path in the table — they can ask).
- **Test** — from the log line.
- **Step** — the success or failure message, which describes what the act was doing.

Mark each row by its cross-reference outcome: **(earlier run)** when an older `.ocarina_logs_*` root names the shot, **(no log)** when no root does
(orphaned — a probe or a manual click). A row with neither marker is confirmed fresh — it belongs to the run named by `$latest_logs`.

## Opening a shot

Reading an image is a separate motion (the framework's `Read` tool handles images). The skill produces the listing; the user (or a follow-up action)
opens the specific shots they care about.

A common follow-up pattern: a failure burst is four shots taken in ~milliseconds — the differences across the four are sometimes the diagnostic (a
toast appears in shot 2, gone by shot 4). Open all four when investigating one failure.

## Stop. The user decides what to open.

The skill picks and surfaces. Decisions about what to view come from the user.

## Examples

### After a run with both passes and a failure

```bash
ls -t <screenshots-dir>/*.png | head -12
```

Result: 4 FAIL*<uuid>*<1..4>.png (one burst, the back-button BFcache test failing on Chrome as expected — §B-BROWSER-1), and 8 PASS shots from the
surrounding tests. The table groups the four FAIL shots as one event so the listing reads as **5 events**, not 12 unsorted files.

### After a clean run (no failures)

12 PASS shots. The table reads as the journey across whichever tests just ran — one row per `log_and_screenshot` call, mtime descending.

### Sorting trap — what NOT to do

```bash
# wrong — UUIDs sort lexicographically, not by recency
ls <screenshots-dir>/*.png | head -12
```

This returns the _alphabetically-first_ 12 files. For a directory that has accumulated hundreds of runs, those 12 are almost certainly **not** the
most recent. The rule is in the description for a reason.

## When to run this skill

- The user asks: "show me the latest screenshots", "what did the fail burst look like?", "let me see the report visually", "what does test X's last
  shot show?"
- Right after a local cycle run, before reviewing.
- After a screenshot-rule change (e.g. screenshot-per-`drive_page` rollout) to eyeball the resulting report.
- When `review-suite-stability` surfaces a flake — the burst shots may show what was on screen.

## What this skill does NOT do

- It does not sort by filename. Ever.
- It does not delete or move shots. The screenshots dir is left as-is; cleanup is a separate motion (often handled by the workflow's
  `--dont-force-delete-tmp-dirs` and Ocarina cleanup).
- It does not open images by itself — the listing is the deliverable; opening is a follow-up tool call.
- It does not infer "this shot proves X" — it ties shots to log lines, the human reads the shots.
