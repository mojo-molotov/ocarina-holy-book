---
name: pick-reports
description:
  Locate and surface reports after a cycle run — both the **DOCX proofs** (one per test, embedding screenshots) and the **JSON results** (one per run,
  machine-readable pass/fail per test). The report directories aren't a fixed convention — they're configured in `main.py` (the file that calls
  `bootstrap(...)` and wires `generate_docx_proof(output_root=...)` / `generate_json_results(output_dir=...)`). The skill **reads `main.py` to find
  the configured paths**, then falls back to a filesystem walk if the wiring is opaque. Once located, run subdirs (`<run-id>/`) and JSON filenames
  (`<uuid>.json`) carry random suffixes, so the latest run is **always** picked by **mtime**, never by filename. Same discipline as `pick-screenshots`
  and `pick-logs`. Use whenever the user asks to read the latest DOCX proof, eyeball a report visually, grab the latest JSON result, parse pass/fail,
  audit report-quality after a screenshot-rule change, or pair with `review-suite-stability` for stability analysis.
---

# Pick reports — by mtime, never by filename

Same rule as `pick-screenshots` and `pick-logs`. The report directories aren't fixed — they're configured in the project's `main.py` (or whichever
file calls `bootstrap(...)` / `_run_plugins(...)`), via `generate_docx_proof(output_root=...)` and `generate_json_results(output_dir=...)`. **Read the
config before guessing the path.**

## Locate the configured report paths

### Step 1 — Read the bootstrap call

```bash
# Find the entrypoint that wires generate_docx_proof / generate_json_results
grep -rn "generate_docx_proof\|generate_json_results" src --include="*.py"
```

Open that file. Look for the `output_root=` (DOCX) and `output_dir=` (JSON) arguments. They are typically `Path(".reports") / "docx"` and
`Path(".reports") / "json"` — but **never assume**. Read the real values from the file.

### Step 2 — Fall back to filesystem if config is opaque

If the bootstrap wiring uses a helper that hides the path, or the project doesn't expose it cleanly:

```bash
find . -type d -name "docx" -path "*/.reports/*" 2>/dev/null | head -3
find . -type d -name "json" -path "*/.reports/*" 2>/dev/null | head -3
# Or more broadly:
find . -type d -name ".reports" 2>/dev/null | head -3
```

The first match (mtime-sorted) is your starting point.

### Step 3 — Common shape (when the project uses Ocarina's defaults)

Once the paths are known, the structure inside is conventional:

```
<configured-reports-root>/
  docx/
    <run-id>/                       # one dir per run; <run-id> is a random suffix
      <Campaign>/
        <Suite>/
          <Test name>.docx          # one DOCX per test, embeds the screenshot sequence
  json/
    <uuid>.json                     # one file per run; machine-readable nested results
```

The `<run-id>` and `<uuid>` are random. **Picking by sort order over the names returns the wrong run.** Always sort by mtime — `ls -dt`, `ls -t`, or
`os.path.getmtime`.

## Pick the latest run

Substitute the path you resolved in steps 1–2 above for `<reports-root>` below.

### DOCX side

```bash
latest_docx_run=$(ls -dt <reports-root>/docx/*/ 2>/dev/null | head -1)
echo "$latest_docx_run"
```

### JSON side

```bash
latest_json=$(ls -t <reports-root>/json/*.json 2>/dev/null | head -1)
echo "$latest_json"
```

If nothing matches, no run has produced reports yet — say so and stop.

### When the user wants multiple recent runs

For comparing two consecutive runs (e.g. before / after a refactor, or stability across replays):

```bash
ls -dt <reports-root>/docx/*/ 2>/dev/null | head -3
ls -t  <reports-root>/json/*.json 2>/dev/null | head -3
```

## DOCX listing — per-test files under the latest run

```bash
find "$latest_docx_run" -name "*.docx" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -<N>
# macOS:
find "$latest_docx_run" -name "*.docx" -type f -exec stat -f '%m %N' {} + | sort -rn | head -<N>
```

Default `N = 20` — usually enough to surface every test in a run; override on request.

## JSON contents — parse pass/fail

The JSON is nested by `<Campaign>/<Suite>/<Test name>`, with each leaf entry shaped like
`[{"status": "success" | "fail", "error": "..."}, <n>, "<test name>"]`.

Quick per-test PASS/FAIL extraction:

```bash
./.venv/bin/python -c "
import json, collections
d = json.load(open('$latest_json'))
c = collections.Counter()
fails = []
def walk(o):
    for k, v in o.items():
        if isinstance(v, dict): walk(v)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            s = v[0].get('status', '?')
            c[s] += 1
            if s != 'success':
                fails.append(k)
walk(d)
print('counts:', dict(c))
for n in sorted(set(fails)):
    print('FAIL', n)
"
```

This is the same parse `review-suite-stability` uses; it's reliable and project-tested.

## Surface — structured tables

Output:

```markdown
# Reports — `<reports-root>/` (top by mtime)

## Latest run

- DOCX run dir: `<reports-root>/docx/<run-id>/` — mtime <date>
- JSON result: `<reports-root>/json/<uuid>.json` — mtime <date>

## DOCX per-test (top N by mtime under the run dir)

| #   | Modified            | Test                                                         | Path        |
| --- | ------------------- | ------------------------------------------------------------ | ----------- |
| 1   | 2026-05-15 18:42:30 | Logout - Session Cleared (via sidebar link)                  | <full path> |
| 2   | 2026-05-15 18:42:28 | Logout - Server-side session invalidation enforced on reload | <full path> |
| ... | ...                 | ...                                                          | ...         |

## JSON summary

- counts: `{'success': 29, 'fail': 6}` (from the parse — see note in §7 of `CURA_TEST_STRATEGY.md`: totals are inflated by `--workers` clones;
  per-test status matters, not the total)
- failures:
  - Appointment - Past date booking accepted
  - Appointment - Server accepts empty date when client bypass applied
  - Appointments - Duplicate booking (same facility, date, program)
  - Appointments - Overlapping appointments (same date, different facilities)
  - Journey - History ordered most-recent date first
  - Logout - Back-button does not restore authenticated history view _(Chrome only; expected per FRD §9.11)_
```

Always include:

- The **latest DOCX run dir** and the **latest JSON file**, with their mtimes — those are the two things 90% of pickings want.
- A per-test DOCX listing **only when the user asked**, or when investigating one specific test (most users want one DOCX to open, not a dump).
- The JSON parse **summary**, not the raw JSON dump — and per `CURA_TEST_STRATEGY.md` §7 (and the `review-suite-stability` skill), do not lead with a
  raw total; the categories are what matter.

## Opening a DOCX or reading the JSON

Reading the JSON is a separate motion (`Read` the path). Opening a DOCX is the user's call — `Read` can extract text but the _visual_ journey is what
makes the DOCX valuable, and that's local-app territory.

The standard motion: pick the right DOCX (one row from the per-test listing), then have the user open it with their viewer; or pick the JSON, parse it
with the snippet above, hand off to `review-suite-stability` for stability analysis across replays.

## Stop. The user decides.

Like the other two `pick-*` skills, this is navigation only — surface the locations and the per-test breakdown, the user reads/opens what they need.

## Examples

### Right after a run

```bash
ls -dt <reports-root>/docx/*/ | head -1
# → <reports-root>/docx/9d0b/
ls -t  <reports-root>/json/*.json | head -1
# → <reports-root>/json/e0da3b42.json
```

Surface both; user opens the JSON for pass/fail at a glance, or picks one DOCX for visual review.

### Eyeballing a report after a screenshot-rule change

The user just landed the screenshot-per-`drive_page` rollout. They want one rich scenario's DOCX to confirm the report replays the journey:

```bash
find "$latest_docx_run/CURA E2E/User journeys/Cross-feature flows" -name "Journey*.docx"
```

Hand the path; user opens it; per-`drive_page` screenshots should make the journey legible end-to-end.

### Comparing two runs (e.g. before / after a fix)

```bash
ls -dt <reports-root>/docx/*/ | head -2
ls -t  <reports-root>/json/*.json | head -2
```

Two paths each; pair the corresponding DOCX run dir with its JSON (by run wall-clock, the pair has near-identical mtimes — they were written in the
same `run_plugins` invocation in `main.py`). Useful for the `review-suite-stability` flow.

### Sorting trap — what NOT to do

```bash
ls <reports-root>/json/ | head -1   # wrong — alphabetical, returns the lexicographically-first JSON
ls <reports-root>/docx/ | head -1   # wrong — same
```

Use `-t` (sort by mtime). Same rule as in `pick-screenshots` and `pick-logs`. The UUID/run-id prefixes are random; alphabetical order is meaningless.

## When to run this skill

- The user asks: "show me the latest report", "where's the DOCX", "give me the JSON results", "what passed / failed in the latest run?"
- After a local cycle run.
- After a screenshot-rule change — eyeball the resulting DOCX to confirm the report replays the journey (the BL-002 follow-up in this project's
  backlog).
- Companion to `review-suite-stability` (which consumes JSON across replays).
- Companion to `pick-screenshots` / `pick-logs` when investigating one specific test (DOCX = visual; logs = chronology; shots = raw frames).

## What this skill does NOT do

- It does not sort by filename. Ever.
- It does not delete or move reports.
- It does not open a DOCX itself — local-app territory.
- It does not aggregate or grade — `review-suite-stability` is the analysis layer; this is the navigation layer.
- It does not lead with totals. The JSON parse summary is grouped by status; counts are _informational, not load-bearing_ (see `CURA_TEST_STRATEGY.md`
  §7's "do not track a total" rule).
