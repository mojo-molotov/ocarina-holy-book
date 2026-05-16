---
name: analyse-screenshot-flakiness
description:
  "**Hunt flakiness by visually comparing screenshots** from repeated runs of the same test — looking for overlays, pop-ups, banners, modals, toasts,
  or any chrome that appears in some captures but not others and has *nothing to do with the test's intent*. The same step, same browser, same
  fixture: in 5 of 10 runs the page is clean; in 3 of 10 a cookie banner covers the submit button; in 2 of 10 a 'session refreshed' toast slides in
  mid-action. That intermittent overlay is the flake. The skill picks the relevant screenshot sets (per `pick-screenshots`), groups them by test +
  step + browser, surfaces the visually anomalous frames, and **triages each anomaly into an adaptation strategy**: (a) a non-blocking overlay
  (notification, ad, toast) → candidate for an Ocarina `Watcher` that observes-and-reports without interrupting; (b) a structurally recognizable
  intermediate page (cookie banner with Accept, an interstitial modal, a consent gate) → candidate for an Ocarina `match_page` branch that dismisses
  it deterministically; (c) a transient artifact of the run (mid-redirect frame, BFcache stale frame) → no adaptation, cross-reference to the gap
  inventory. Use whenever the user asks to compare screenshots across runs, find what's making screenshots different, decide whether to add a watcher
  or a match_page branch, or triage visual flakes."
---

# Analyse screenshot flakiness — what's in the picture that shouldn't be?

A diagnostic skill. The screenshots from `<gitignored>/screenshots/` (mtime-sorted, per `pick-screenshots`) are the **only** record of what the page
_actually looked like_ at the moment of capture. Repeated runs of the same test produce N copies of the same captures, in principle identical. In
practice, intermittent overlays — cookie banners, session-refresh toasts, ad iframes, autoplay nags, third-party widget loaders — appear in some
frames and not others, and that visual delta _is_ the flake.

The skill is the bridge between **"the screenshots look different"** and **"here is the Ocarina adaptation that absorbs the difference
deterministically"**.

## The three adaptation paths (the triage)

For each anomaly the skill surfaces, the user picks one of three responses. The skill recommends; the user decides.

### Path A — `Watcher` (non-blocking observability)

When the overlay is a **non-blocking** signal that doesn't change the user's flow:

- A `session refreshed` toast that auto-dismisses.
- A telemetry / cookie-consent banner that the user can ignore.
- A console error / warning surfaced as an in-page banner.
- A "new feature!" notification overlay that doesn't block clicks.

These don't break the test (the click still lands), but they **should be observed and reported** so the team knows they exist. The Ocarina `Watcher`
(see `analyse-watcher-flakiness`) is built for exactly this — daemon thread, polls for the overlay, reports + screenshots without interrupting the
test chain.

Recommend `Watcher` when: the overlay is intermittent, doesn't block the next test action, and the team would want to _know_ it appears.

### Path B — `match_page` branch (deterministic dismissal)

When the overlay **does** block the user's flow but is structurally recognizable:

- A cookie-consent banner that hides the page until Accept is clicked.
- An interstitial "are you sure?" modal that intercepts a navigation.
- A login-extension prompt: "Stay logged in? [Yes] [No]".
- A consent gate: "I am over 18".

These need to be **handled deterministically** — the test can't proceed until the overlay is dismissed. Ocarina's `match_page` (see
`<gitignored>/ocarina/.../dsl/testing_with_railway/match_page.py`) is built for this: declare branches, dismiss the overlay when matched, fall through
when it doesn't appear.

Recommend `match_page` when: the overlay blocks the next action, has a stable structure (selector + dismiss button), and appears predictably enough
that a branch can match it.

### Path C — Transient run artifact (no adaptation; cross-reference)

When the overlay is **not** a real UI element but an artifact of the _capture moment_:

- A mid-redirect frame (the screenshot landed during a `302`-then-load).
- A BFcache stale frame (Chrome restored a snapshot of a previous page) — already documented as `§B-BROWSER-1`.
- A driver-level rendering glitch (chromedriver captured before paint).

No Ocarina adaptation fixes this — it's not a UI element to handle. The adaptation is a cross-reference: the symptom already lives in the gap
inventory, or it should be filed as a new entry.

Recommend cross-reference when: the anomaly isn't a real DOM element but a transport / cache / timing artifact.

## Procedure

### Step 1 — Restate the question

"Test_appointment_booking has been intermittently failing at the submit step — pull the last 10 screenshot bursts and compare." Or "I noticed a banner
in some failure shots; is it consistent enough to handle?" Or "Audit all recent failure screenshots — are there overlays I missed?"

### Step 2 — Pick the screenshot set

Per `pick-screenshots`: **always mtime-sorted, never filename-sorted**. UUID suffixes are random.

```bash
ls -t <gitignored>/screenshots/ | head -<count>
```

For a "10 runs of the same test" comparison: pull the last 10 bursts of that test's step. For an "audit recent failure shots" pass: pull the last 50
shots across all tests, then group by test + step.

Capture the **log line** that produced each screenshot — the cross-reference is non-negotiable. Without it, you're staring at pictures with no
provenance.

### Step 3 — Group by (test, step, browser)

Build a small index:

```
test_appointment_booking / submit / chrome:
  - shot_2026-05-15T14-22-01-abc123.png  (run 1, log line 4421)
  - shot_2026-05-15T14-25-09-def456.png  (run 2, log line 4598)
  - shot_2026-05-15T14-28-14-ghi789.png  (run 3, log line 4773)
  - ...

test_appointment_booking / submit / firefox:
  - ...
```

Each group is the comparison unit. Don't cross-compare groups; chrome and firefox render differently, and a "missing banner in firefox" might just be
a different browser policy.

### Step 4 — Visually compare within each group

For each group, view all N shots side-by-side (or in sequence). For each shot, capture three observations:

- **Page content** — is the expected element present and in the expected state?
- **Overlay / chrome present** — banners, toasts, modals, iframes, widgets, system dialogs.
- **Anomaly score** — does this shot match the "clean" majority, or does it have an outlier element?

A useful rule: the **mode** of the group is the baseline. Anything that appears in a minority of shots is the candidate flake.

If the group has no mode (every shot is different), the flake isn't a discrete overlay — it's probably timing (mid-render captures). Move to Path C.

### Step 5 — For each anomaly, recommend a path

Triage criteria, in order:

1. **Does the overlay block the next action the test takes?**
   - If yes → likely Path B (`match_page`). Confirm with: does it have a stable selector + dismiss button?
   - If no → Path A (`Watcher`) or Path C (artifact).
2. **Is the overlay a real DOM element you can capture HTML for?**
   - If yes → Path A or B (depending on blocking).
   - If no (it's a render artifact, a partial frame) → Path C.
3. **Does the team want to _know_ this overlay exists?**
   - If yes → Path A even if non-blocking (the watcher reports).
   - If no (e.g. a known cosmetic blip) → no adaptation; ignore.

### Step 6 — Surface the findings

```markdown
# Screenshot-flakiness analysis — <one-sentence question>

## Sets compared

- `<test> / <step> / <browser>` — <N> shots, <date range>.
- ... (one bullet per group)

## Anomalies

### `<test> / <step> / <browser>`

- **Mode (baseline)**: <description> — <N>/<total> shots.
- **Anomaly 1**: `<concrete overlay description>` — <K>/<total> shots.
  - Sample frames: `<file>`, `<file>`, `<file>` (paths under `<gitignored>/screenshots/`).
  - Blocks next action? <yes | no>.
  - Real DOM element? <yes | no | unclear>.
  - **Recommended path**: <A: Watcher | B: match_page | C: cross-reference>.
  - Rationale: <one sentence>.

- **Anomaly 2**: `<…>` — …

## Recommended adaptations

### Path A — `Watcher` candidates

- `<name>` for `<overlay>`. Suggested poll_interval: `<s>`. Audit before merging per `analyse-watcher-flakiness`.

### Path B — `match_page` branches

- In `<scenario file>` at the `<step>` step, add a branch matching `<selector>` and dismissing via `<click on …>`. Cross-reference: Ocarina
  `match_page` docs (`<gitignored>/ocarina/.../match_page.py`).

### Path C — Cross-references (no adaptation)

- `<anomaly>` matches `the gap inventory <entry-ref>` — already documented.
- `<anomaly>` is new → file as `B-*` / `A-ENV-*` / `G-*` (user picks the prefix).

## Cross-references

- the gap inventory <entry-refs>.
- `analyse-watcher-flakiness` (for Path A planning).
- `pick-screenshots` (for the source rule used to pick these shots).

## Open follow-ups

- <anomaly without enough samples> — pull more runs, re-audit.
- <ambiguous overlay (could be DOM or render artifact)> — invoke `write-a-probe` to capture `outerHTML` at the suspected moment.

## Verdict

<one-line: N anomalies, K → Watcher, J → match_page, M → cross-ref, nothing material>.
```

Print the findings. Do not write to a file unless the user asks.

### Step 7 — Stop. The user decides.

Each recommendation resolves as:

- **Path A applied** — author the watcher (the _user_ writes the scenario change; this skill doesn't), then run `analyse-watcher-flakiness` before
  merging.
- **Path B applied** — extend the scenario with a `match_page` branch + dismissal step. The skill _describes_ the branch shape; the user writes it.
- **Path C applied** — extend the gap inventory (via `update-frd-and-tests` or a direct edit) so the next reader doesn't re-investigate.
- **Defer** — interesting but rare; revisit if it recurs.

## Hard rules

- **Always mtime-sort screenshots, never filename-sort.** Per `pick-screenshots` — UUID suffixes are random.
- **Always group by (test, step, browser).** Cross-group comparisons confuse the analysis.
- **The mode is the baseline.** Don't anchor on the first shot; anchor on the majority.
- **Don't recommend an adaptation for a single anomalous frame.** One outlier across 10 runs might be a render artifact (Path C). A pattern across
  multiple runs is what justifies Path A or B.
- **Don't combine paths arbitrarily.** A given anomaly should resolve as exactly one of A / B / C. A watcher _and_ a match_page branch for the same
  overlay is usually a confused diagnosis.
- **Cite the log line for every shot.** Provenance is non-negotiable — without it, the comparison is unverifiable.
- **Don't suggest probing with attack-shape inputs.** Per `CLAUDE.md` → "Security testing is functional and static — never active". An iframe ad is a
  Path A candidate, not a security investigation.

## When to run this skill

- A test fails intermittently and the failure screenshots look subtly different across runs.
- After a SUT deployment — has anything new started appearing in screenshots?
- Before adding a `Watcher` or a `match_page` branch — confirm with empirical screenshot evidence that the overlay is real and recurrent.
- During a `review-suite-stability` pass that surfaces a SURPRISE RED on a previously-stable test — visual comparison often reveals an overlay landed
  in the test path.
- Onboarding — a screenshot tour of "what overlays we already handle" feeds back to the FRD.

## What this skill does NOT do

- It does not write the watcher or the match*page branch. It \_describes* the adaptation; the user authors it.
- It does not pull screenshots blindly from a directory — it follows `pick-screenshots`'s rules (mtime sort, log cross-reference, group by test/step).
- It does not run probes. If an anomaly's DOM origin is unclear, the next motion is `write-a-probe` (capture `outerHTML` at the suspected moment), not
  more screenshot staring.
- It does not modify Ocarina's `Watcher` / `match_page` contracts. Audit those via `analyse-watcher-flakiness`.
- It does not update the gap inventory directly. Cross-references are _recommended_; the entry itself is a follow-up via `update-frd-and-tests`.
- It does not include attack-shape inputs in any sample. An overlay carrying suspicious content (e.g. a clickjacked iframe) is filed as a gap, not
  probed actively.
