---
name: propose-visual-review
description:
  Surface the headed / headless choice **before** the user dispatches a local run — should they watch the browser play out (`--not-headless`) or run
  headless (CI-shaped, the default). Visual review is for diagnosis, demos, pairing, sanity-checking a refactor, building intuition about the SUT;
  headless is the canonical shape that matches CI. Walk the trade-off in one short prompt, compose the final `python src/main.py ...` command, hand
  it back — the user runs it. Use whenever the user is about to dispatch a run: _"I'm going to launch the tests"_, _"rerun X"_, _"kick off a cycle
  locally"_, _"let me see what happens on Y"_. Also after `write-a-probe` lands a finding the user wants to see by eye, before a pairing session, or
  before a demo where the visual _is_ the artifact. Do not dispatch the run yourself — the choice is the user's, and a windowed run usually wants
  the user already at the keyboard.
---

# Propose visual review — headed or headless?

A pre-run prompt. `--not-headless` shows the browser UI as Ocarina drives it; headless (the default) runs without a window. The two have different
purposes — surface the call before the user types the command, so they get the run shape they actually want, not the one they typed by reflex.

This skill never dispatches the run. It walks the choice, composes the command, hands it back. Same _"surface, don't apply"_ rule as the rest of the
suite — running it is the user's motion.

## When visual review is the right call

- **Diagnosing an unexpected symptom.** A test went red and the DOCX proof / JSON result / screenshots don't fully explain why. Watching the journey
  at runtime shows the transient states (a toast that flashes, a modal that dismisses itself, focus stealing) that snapshots miss between frames.
- **Sanity-checking a refactor.** After a POM rewrite, a selector swap, a connector consolidation — headless green is correctness; a visual
  confirmation is _"yes, the user-facing journey still looks right"_.
- **Building intuition about a new SUT or a new feature.** First contact is faster watching the suite drive it than reading the scenario cold.
- **Pairing or demo.** The visual _is_ the artifact: showing a colleague what a gap test exposes, walking a stakeholder through saturation, showing
  the matrix actually clicking through CURA in three browsers.
- **Verifying a probe-confirmed finding by eye.** `write-a-probe` captured the state; the headed run shows it in motion.

## When headless is the right call

- **Canonical runs.** CI is headless. A run whose green/red counts as _"the suite passes"_ must be headless — anything else diverges from CI and stops
  being a reliable signal.
- **Speed.** Headless is faster: no rendering, no compositor, no window management.
- **Long / batch / overnight / dispatched.** Headless runs in a tmux pane, a CI dispatch, a scheduled cron; headed mode steals focus and assumes
  someone is watching.
- **The DOCX proofs already answer the question.** Per `CLAUDE.md` → _"Reports and screenshots"_, every run writes a per-test DOCX with a screenshot
  at every page transition. If reading the proof would settle the question, watching the run live adds nothing.

## What to look for during a headed run

A visual run is wasted if the user blinks through it. Things headless / DOCX cannot show:

- **Transient overlays** — toasts, flash banners, autocomplete dropdowns, password-manager prompts, breach modals (per `CLAUDE.md` → _"Form submission
  paths"_ and the §A-ENV-2 environmental artifact). The framework's failure-burst screenshots catch some; the live frame catches the rest.
- **Focus drift** — windows competing for focus under `--workers ≥ 2`, the browser stealing focus mid-`send_keys`. A "Form didn't submit" symptom
  often resolves here.
- **Pacing** — the run feels rushed or racing? That's a wait-strategy smell. Don't bump `--wait-timeout` to compensate; note where the eye couldn't
  keep up and follow with `analyse-flakiness` / `question-state`.
- **Widget intercepts** — date-pickers, autocompletes, masked inputs. The visual confirms the suite is driving the widget's API rather than fighting
  it (per `CLAUDE.md` → _"Widget-decorated inputs"_).
- **Cross-browser cosmetics** — a divergence the matrix surfaces but DOCX doesn't quite explain (BFcache snapshots restoring stale content, Firefox
  re-requesting; Chrome's password-breach modal swallowing input on a clean profile when the adapter is bypassed).

## Tension with `--workers N`

`CLAUDE.md` is firm: `--workers ≥ 2`, never `--workers 1`. Visual mode and `--workers N > 1` are not mutually exclusive — N concurrent windows is what
happens — but they jostle for focus and clutter the screen. Two paths:

- **Visual run is for diagnosing one specific test.** Pair `--not-headless` with `--only <test-id>` (or a small subset). The saturation guarantee from
  `--workers N` is irrelevant when the goal is _"watch one journey by eye"_. Keep workers ≥ 2 if the test interacts with a shared SUT resource; just
  know two windows will jockey.
- **Visual run is for a full cycle, demo-shaped.** Accept the multi-window jostling — that _is_ the demo, multiple browsers exercising the SUT in
  parallel. Put windows on a wide monitor; resign yourself to focus drift.

Never use this skill as a back door to `--workers 1`. If the user reaches for it, surface the rule from `CLAUDE.md` and let them confirm — don't
elide.

## Other flags that pair with visual mode

- **`--logger terminal`** when the visual run is throwaway diagnosis — no DOCX needed, terminal logs are enough alongside the live frame.
- **`--logger terminal+file`** when the visual run is the artifact (a demo whose recording you'll keep) — DOCX proofs travel with the recording.
- **`--wait-timeout`** — leave it alone. Visual mode tempts the user to slow the suite down so they can watch each step; if you need beat-by-beat
  observation, that's `manual-reproduction-guide` territory, not a timeout bump.
- **`--profile-path`** — when the visual goal is checking how a user-with-state experiences the journey (saved logins, cookie consents, autofill).

## Procedure

### 1. Confirm the user is about to dispatch a run

Triggers: _"I'm going to launch the tests"_, _"rerun X"_, _"let me see what the suite does on Y"_, _"kick off a local cycle"_. If the user is not yet
at the dispatch step (still authoring, still reviewing a report), step back — this skill is the pre-run prompt, not a general guidance one.

### 2. Ask the visual-or-headless question

One short prompt. Don't pre-decide; don't recite every trade-off. Examples:

- _"Headed (`--not-headless`, you watch the browser) or headless (default, CI-shaped)?"_
- _"Want to see this run live, or run it headless like CI?"_

If the user asks for the trade-off, point at the two _"When … is the right call"_ sections above. The choice is theirs.

### 3. Compose the final command

Take the user's choice + their other flags (driver path, browser, workers, wait timeout, logger, `--only` / `--exclude`) and assemble the full
command. Use the canonical script form per `CLAUDE.md` → _"Running tests"_ (script form, `src/` as source root — never `python -m src.main`):

```bash
python -u src/main.py \
  --driver-path <path/to/chromedriver> \
  --browser <chrome|firefox|edge|safari> \
  --workers <N>            # ≥ 2
  --wait-timeout 10 \
  --logger <terminal|terminal+file> \
  [--not-headless] \
  [--only <id> ...]
```

If headed: flag included. If headless: flag omitted (it's the default — don't append a no-op).

### 4. Print the command. Hand it back.

The user runs it. Do not dispatch — the user may want to adjust monitor placement, start a screen recording, swap profile, or sanity-check the flag
set before pressing return. Headed runs especially benefit from "user already at the keyboard when it starts".

### 5. (Optional) Suggest the follow-up

After a visual run, common next moves:

- The visual confirmed a finding → `manual-reproduction-guide` to produce the human-runnable companion, or `write-a-probe` for machine-readable
  evidence.
- The visual surfaced a flake → `question-state` first (environmental cause is cheap to rule out), then `analyse-flakiness` /
  `analyse-screenshot-flakiness`.
- The visual showed a cross-browser divergence → `manual-reproduction-guide` Layer 3, or extend the matrix entry.
- The visual showed nothing surprising → headless rerun for the canonical signal; the visual was the sanity check, not the verdict.

## What this skill does NOT do

- It does not dispatch the run. Composes the command, hands it back; the user types or pastes.
- It does not decide between headed and headless for the user. Trade-offs are surfaced; the call is theirs.
- It does not relax `--workers ≥ 2`. Visual mode is not a license to single-thread the suite.
- It does not replace the DOCX proofs. If the visual run is for keeping, `--logger terminal+file` is still required — visual ≠ durable artifact.
- It does not record video or capture the visual run. Screen recording is the user's tool of choice (QuickTime, OBS, `screencapture -V`,
  `wf-recorder`); the skill stops at _"run it like this"_.
- It does not run the visual review for the user. The eye on the screen is theirs — the framework can drive the browser, but it can't watch it.

## When to run this skill

- The user says they're about to launch a run.
- After `write-a-probe` lands a finding the user wants to see by eye.
- Before a pairing session or a demo run where the visual is the artifact.
- After a refactor that touches POM mechanics — a headless green plus a quick headed confirmation is a tighter signal than headless alone.
- When a flake survives a `question-state` walk and a headless rerun — a headed replay can surface the transient state both missed.
