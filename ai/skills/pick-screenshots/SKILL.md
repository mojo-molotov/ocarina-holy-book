---
name: pick-screenshots
description:
  List and surface the N most recent screenshots after a cycle run — sorted strictly by **file modification time**, never by filename. Filenames carry
  random UUID suffixes (`PASS_<uuid>.png`, `FAIL_<uuid>_<n>.png`) that don't sort meaningfully by recency, so any naive alphabetical/`ls` listing
  returns the wrong files. The screenshot directory isn't a fixed convention — it's determined by the **test code's** screenshot handler factories
  (typically configured in `src/lib/ext/ocarina/adapters/selenium/logs.py` or similar, with calls like `create_log_success_and_take_screenshot(...)`).
  The skill **reads the screenshot factory wiring** to find the configured path, then falls back to a filesystem walk. Use whenever the user asks to
  see the latest screenshots, look at the fail burst from a recent run, inspect a passing test visually, or audit the report-quality after a
  screenshot-rule change. Cross-reference each screenshot to the log line that names it so the user sees which test, which step, which page each shot
  belongs to.
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

The Ocarina log writes a line per shot:

```
[UTC_DATE::…] ℹ️  CURA E2E/Authentication/Session management/Logout - Session Cleared (via sidebar link) — Screenshot: /…/PASS_<uuid>.png
```

The line carries: the test path (campaign / suite / test name), and the absolute path of the file. Grep across the most recent log tree:

```bash
# locate the latest log root
latest_logs=$(ls -dt <logs-parent>/.ocarina_logs* 2>/dev/null | head -1)
# for one screenshot path:
grep -rh "PASS_<uuid>.png" "$latest_logs"
```

If the log root doesn't contain a hit (the screenshot is from an earlier run), widen across all `.ocarina_logs_*` roots — accept that you may now be
reading two runs' worth.

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

If a screenshot has no corresponding log line in any `.ocarina_logs_*` (the run was deleted, the screenshot orphaned), mark **(no log)** and surface
it — it may be from a probe or a manual click.

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

Result: 4 FAIL*<uuid>*<1..4>.png (one burst, the back-button BFcache test failing on Chrome as expected — `IDENTIFIED_GAPS.md` §B-BROWSER-1), and 8
PASS shots from the surrounding tests. The table groups the four FAIL shots as one event so the listing reads as **5 events**, not 12 unsorted files.

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
