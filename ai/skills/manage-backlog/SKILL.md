---
name: manage-backlog
description:
  Two-mode skill for the repo's `BACKLOG.md` — **generate** a backlog by scanning project state (TODO/FIXME comments, `IDENTIFIED_GAPS.md`,
  `CURA_FRD.md` §9 hardening recommendations, stored skills not yet run, release-hardening items the session surfaced) and **ingest** a backlog (from
  a paste, a file, or `gh issue list`) by normalising items into the project's schema and merging — with dedup — into `BACKLOG.md`. Use whenever the
  user asks to draft a backlog, refresh the backlog, ingest tickets, import issues, list open follow-ups, plan a release, or audit what's still on the
  table. Surface items for review before persisting — a backlog is authoring data, and a silent commit hides the author's choices about scope and
  priority.
---

# Manage backlog — generate / ingest

Two-mode skill for one canonical `BACKLOG.md` at the **repo root** (`/Users/causticbitch/Documents/Delivery/ocarina-doc/BACKLOG.md`). The repo spans
more than the project root (the project has skills, docs, workflows), so the backlog lives at the repo root, not inside the project root.

The two modes share one item schema and one on-disk format. Both modes end the same way: **present the candidate items for the user's review, then
persist after approval.** A backlog is a dataset — silently writing it imposes the author's prioritisation; surfacing it surfaces the decision.

## Item schema (the load-bearing dataset)

Every item carries these fields (extra fields allowed only if the user adds them):

| Field         | Required | Values                                                                                                                               |
| ------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `id`          | yes      | `BL-NNN`, stable, three-digit zero-padded, never reused                                                                              |
| `title`       | yes      | one short line, action-led                                                                                                           |
| `type`        | yes      | `feat` / `refactor` / `fix` / `doc` / `test` / `audit` / `followup` / `release`                                                      |
| `priority`    | yes      | `P0` (block ship) / `P1` (next) / `P2` (later) / `P3` (nice-to-have)                                                                 |
| `status`      | yes      | `open` / `in-progress` / `done` / `blocked` / `wontfix`                                                                              |
| `source`      | yes      | where this came from — `session-2026-05-15`, `TODO: src/.../foo.py:42`, `IDENTIFIED_GAPS.md §B-BROWSER-1`, `paste`, `gh issue #N`, … |
| `description` | yes      | 1–3 sentences. What and why.                                                                                                         |
| `acceptance`  | optional | what "done" means concretely                                                                                                         |
| `deps`        | optional | other `BL-NNN` IDs this depends on                                                                                                   |

IDs are assigned by reading the highest existing `BL-NNN` in `BACKLOG.md` and incrementing. Don't recycle IDs of items moved to `done` / `wontfix` —
they stay in the file for history.

## Format on disk — `BACKLOG.md`

One H1, one section per item (H2). Status filter at the top so a reviewer sees open work first:

```markdown
# Backlog

> Living list of open follow-ups, hardening items, and gaps. Don't track in two places — if it ends up here, the conversation about it points here.
> `done` and `wontfix` items stay for history.

## BL-001 — Run full Firefox+Chrome matrix on `main` HEAD as the release baseline

- **Type**: release
- **Priority**: P0
- **Status**: open
- **Source**: session-2026-05-15 (release-hardening review)
- **Description**: The last four PRs (#23–#26) merged with delta runs only. A canonical the e2e workflow workflow dispatch on `main` HEAD is the
  release baseline. Expected outcome: 5 intentional gap fails + 2 chrome BFcache reds, nothing else.
- **Acceptance**: GA dispatch on `main` HEAD; both browsers complete; only documented reds.

## BL-002 — Eyeball a generated DOCX proof after the screenshot-per-`drive_page` change

- **Type**: audit
- **Priority**: P1
- **Status**: open
- **Source**: session-2026-05-15 (maturity review)
- **Description**: The screenshot-per-`drive_page` rule landed on every scenario, but no human has opened a generated DOCX to confirm it reads as a
  coherent journey. Pick one rich scenario (e.g. `Journey - Book Appointment and Verify in History`) and read its DOCX end-to-end.
- **Acceptance**: User opens one DOCX; confirms the page sequence reconstructs the journey; or files a follow-up `audit` item if it doesn't.

## BL-003 — Run the four new `review-*` skills against `src/` once

- **Type**: audit
- **Priority**: P1
- **Status**: open
- **Source**: session-2026-05-15 (skills authored, never run)
- **Description**: `review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers` were written this
  session but never executed against the source. First run will surface the actual debt — the unverified-transition audit alone is expected to flag
  the `post_logout_*` logout drive_pages.
- **Acceptance**: Each skill reports against `src/`; findings either fixed or filed as further backlog items.

## BL-004 — done — Cover the sidebar Login link

- **Type**: test
- **Priority**: P1
- **Status**: done
- **Source**: session-2026-05-15
- **Description**: The sidebar Login link (logged-out state) had no test; `journey/sidebar_login_navigation.py` closes the gap. Landed in `main`
  `ee8dc02`.
```

The exact rendering can wobble (table for the bullet list is OK; one big table for all items is fine for short backlogs); the **fields and IDs must be
stable**.

## Mode A — Generate

Build a candidate backlog by scanning the project state. The scanning sources, in order:

### Sources to scan

| Source                                       | How                                                                                                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Code TODO / FIXME / XXX / HACK comments      | `grep -rnE "TODO\|FIXME\|XXX\|HACK" --include='*.py' --include='*.md' --include='*.yml' .` from the repo root                                                                                                                                                                                                                                                                                         |
| `IDENTIFIED_GAPS.md` entries                 | Each `G-*` / `B-BROWSER-*` / `A-ENV-*` heading is a candidate. Most are _CURA's_ work, not ours — mark them `type: doc` (we document) unless we have an actionable fix on our side (e.g. `B-BROWSER-1` motivates the recommendation `Clear-Site-Data` — that's a CURA recommendation, still not our backlog). When in doubt: file as `priority: P3`, `description` notes "informational — CURA-side". |
| `CURA_FRD.md` §9 hardening recommendations   | Same logic — informational. Surface only if the user wants them in the backlog.                                                                                                                                                                                                                                                                                                                       |
| Skills written but never run                 | `find skills -name SKILL.md` and check whether any audit/review skill has output evidence anywhere. If not, file an `audit` item.                                                                                                                                                                                                                                                                     |
| Release-hardening items the session surfaced | From the conversation history, the maturity review, or anything the user/Claude flagged as "later" / "follow-up". Mark `source: session-<date>`.                                                                                                                                                                                                                                                      |
| Pending PR follow-ups                        | If a recent PR's description carries a `[ ] pending` item in the Test plan (e.g. "manual the e2e workflow workflow run"), it's a candidate.                                                                                                                                                                                                                                                           |

### Procedure (Generate)

1. **Run the scans.** Print a short summary per source — N TODOs found, M IDENTIFIED_GAPS entries, K skills awaiting first run, etc.
2. **Read existing `BACKLOG.md`** (if any) to learn the highest `BL-NNN` and to dedup. If the file doesn't exist, plan to create it.
3. **Build the candidate item list.** For each unique candidate not already in the backlog, draft the eight required fields. **Do not invent
   priorities silently** — assign a starting priority but flag every priority assignment as the audit's guess, to be confirmed.
4. **Surface for review.** Print the candidate items, grouped by `type`. Ask the user to:
   - Add / remove / merge / split items.
   - Confirm priorities (the audit's are guesses).
   - Confirm titles / descriptions read right.
5. **Persist on approval.** Write `BACKLOG.md`. Append new items, leaving existing ones untouched. Never reorder or rewrite existing items without a
   separate explicit ask.
6. **Stop.** Do not start working on items. Do not file GitHub issues. Do not push.

## Mode B — Ingest

Take an existing backlog (paste in chat, file path, `gh issue list`) and normalise it into the schema, then merge with `BACKLOG.md`.

### Input forms

| Form                  | How                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| Paste in chat         | User dumps lines / a list / a markdown fragment. Parse into items.                             |
| File path             | User points at `path/to/backlog.md` or similar. Read it.                                       |
| GitHub issues         | `gh issue list --state open --limit 100 --json number,title,body,labels` for the current repo. |
| Other tracker exports | CSV, JSON — read it; ask which columns map to which schema field if ambiguous.                 |

### Procedure (Ingest)

1. **Read the input.** Print a short summary: N raw items found.
2. **Normalise each raw item** to the schema. Where a field can't be inferred (priority, type, acceptance), mark `<TBD>` rather than guessing. Drop
   blank fields entirely if optional.
3. **Read existing `BACKLOG.md`** to dedup. For each incoming item, find candidates in the existing backlog by title-similarity (close enough is "same
   item"); list them as `(possible dup of BL-NNN)` rather than skipping silently.
4. **Surface for review.** Print the normalised items, marking `<TBD>` fields and dup candidates explicitly. Ask the user to:
   - Fill `<TBD>` fields.
   - Confirm dedup decisions (merge / keep both / drop).
   - Adjust normalisation where the auto-pass got it wrong.
5. **Persist on approval.** Append accepted items to `BACKLOG.md`, assigning IDs from the next available `BL-NNN`. Update existing items only if the
   user explicitly maps an incoming item onto one.
6. **Stop.**

## Editing `BACKLOG.md` directly

If the user is editing an item by hand (changing status to `done`, bumping priority, adding `acceptance`), do not run the skill — they can edit the
file. The skill is for _adding_ items in bulk (generate / ingest) and for _normalising_ incoming data, not for routine status flips.

## Examples

### Generate — TODO comment in source

```python
# src/lib/foo.py:42
def normalise(value: str) -> str:
    # TODO: handle the Unicode-NFC edge case once we hit it
    return value
```

→ candidate item:

```markdown
## BL-NNN — Handle Unicode-NFC edge case in `normalise`

- **Type**: followup
- **Priority**: P3 (the TODO doesn't claim urgency)
- **Status**: open
- **Source**: TODO at src/lib/foo.py:42
- **Description**: Existing TODO suggests `normalise` should handle a Unicode-NFC edge case. No current observed defect; track for when the case
  lands.
```

The priority is the audit's guess (P3, because the TODO didn't flag urgency). Surface for the user to bump if needed.

### Generate — `IDENTIFIED_GAPS.md` entry

`§B-BROWSER-1 — Chrome restores no-store authenticated pages from BFcache.` Recommendation in the entry: send `Clear-Site-Data: "cache", "cookies"` on
the logout response. That's CURA-side; not our backlog. The audit surfaces it as **informational** with `priority: P3`, `type: doc`, description
"informational — CURA-side hardening recommendation; covered by the cross-browser red tests on our side."

### Ingest — paste from chat

User pastes:

```
- fix the empty profile page
- add safari to CI matrix
- track Chrome version in artifacts
```

Normalised:

```markdown
## BL-NNN — Fix the empty profile page

- **Type**: <TBD — likely fix>
- **Priority**: <TBD>
- **Status**: open
- **Source**: paste, session-<date>
- **Description**: From user paste. Needs clarification — "empty" meaning the §9.2 placeholder gap, or a regression?

## BL-NNN — Add Safari to the CI matrix

- **Type**: feat
- **Priority**: <TBD>
- **Status**: open
- **Source**: paste, session-<date>
- **Description**: Currently the matrix is Firefox + Chrome. Safari requires `safaridriver` (macOS-only runners). Cost/benefit tradeoff worth raising.
```

The `<TBD>`s are surfaced to the user; nothing is invented.

## When to run this skill

- The user asks: "draft the backlog", "refresh the backlog", "what's still open", "list follow-ups", "import these issues", "ingest this list".
- After a major milestone (a release-candidate cut, a big merge series) — capture what was left for next round.
- When a fresh paste lands in chat that looks like backlog material.

## What this skill does NOT do

- It does not start _working_ on backlog items. The skill files and normalises; it does not implement.
- It does not push items to GitHub issues (unless the user explicitly asks).
- It does not silently rewrite existing items in `BACKLOG.md`. Existing items are mutated only on explicit user request.
- It does not guess priorities silently. Every guess is flagged for confirmation.
