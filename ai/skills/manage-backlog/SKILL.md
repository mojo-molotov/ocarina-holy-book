---
name: manage-backlog
description:
  Two-mode skill for the project's backlog — **generate** by scanning project state (TODO/FIXME comments, the gap inventory, the FRD's
  hardening recommendations, stored skills not yet run, release-hardening items the session surfaced) and **ingest** an existing backlog (paste, file,
  Jira export, Confluence page, GitHub issues, JSON, CSV, PDF) by normalising items into one schema and merging — with dedup — into the canonical
  backlog. The on-disk form is interoperable: `BACKLOG.md` at the repo root by convention, but the same schema maps cleanly onto Jira tickets, GitHub
  issues, Confluence pages, or whatever tracker the team picks. Use whenever the user asks to draft a backlog, refresh the backlog, ingest tickets,
  import issues, list open follow-ups, plan a release, or audit what's still on the table. Surface items for review before persisting — a backlog is
  authoring data, and a silent commit hides the author's choices about scope and priority.
---

# Manage backlog — generate / ingest

Two-mode skill for one canonical backlog. The convention is `BACKLOG.md` at the **repo root** (the repo usually spans more than a single project
directory — skills, docs, workflows — so the backlog lives at the repo root, not inside any one sub-project). But the schema is interoperable: the
same fields map onto Jira tickets, GitHub issues, Confluence rows, or a JSON dataset. Pick the on-disk form your team already uses; the skill works
with all of them.

The two modes share one item schema and one normalisation pass. Both modes end the same way: **present the candidate items for the user's review, then
persist after approval.** A backlog is a dataset — silently writing it imposes the author's prioritisation; surfacing it surfaces the decision.

## Item schema (the load-bearing dataset)

Every item carries these fields (extra fields allowed only if the user adds them):

| Field         | Required | Values                                                                                                                                        |
| ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`          | yes      | `BL-NNN`, stable, three-digit zero-padded, never reused (or the tracker's native ID — `JIRA-1234`, `gh-#42`)                                  |
| `title`       | yes      | one short line, action-led                                                                                                                    |
| `type`        | yes      | `feat` / `refactor` / `fix` / `doc` / `test` / `audit` / `followup` / `release`                                                               |
| `priority`    | yes      | `P0` (block ship) / `P1` (next) / `P2` (later) / `P3` (nice-to-have)                                                                          |
| `status`      | yes      | `open` / `in-progress` / `done` / `blocked` / `wontfix`                                                                                       |
| `source`      | yes      | where this came from — `session-YYYY-MM-DD`, `TODO: src/.../foo.py:42`, `<gap-inventory> <entry-ref>`, `paste`, `gh issue #N`, `JIRA-1234`, … |
| `description` | yes      | 1–3 sentences. What and why.                                                                                                                  |
| `acceptance`  | optional | what "done" means concretely                                                                                                                  |
| `deps`        | optional | other item IDs this depends on                                                                                                                |

IDs are assigned by reading the highest existing `BL-NNN` in the canonical backlog and incrementing. Don't recycle IDs of items moved to `done` /
`wontfix` — they stay in the file for history.

## Format on disk — `BACKLOG.md` (the conventional form)

One H1, one section per item (H2). Status filter at the top so a reviewer sees open work first:

```markdown
# Backlog

> Living list of open follow-ups, hardening items, and gaps. Don't track in two places — if it ends up here, the conversation about it points here.
> `done` and `wontfix` items stay for history.

## BL-001 — Run full Firefox+Chrome matrix on `main` HEAD as the release baseline

- **Type**: release
- **Priority**: P0
- **Status**: open
- **Source**: session-YYYY-MM-DD (release-hardening review)
- **Description**: The last four PRs merged with delta runs only. A canonical e2e workflow dispatch on `main` HEAD is the release baseline. Expected
  outcome: the documented intentional gap fails + the cross-browser BFcache reds, nothing else.
- **Acceptance**: GA dispatch on `main` HEAD; both browsers complete; only documented reds.

## BL-002 — Eyeball a generated DOCX proof after the screenshot-per-`drive_page` change

- **Type**: audit
- **Priority**: P1
- **Status**: open
- **Source**: session-YYYY-MM-DD (maturity review)
- **Description**: The screenshot-per-`drive_page` rule landed on every scenario, but no human has opened a generated DOCX to confirm it reads as a
  coherent journey. Pick one rich scenario and read its DOCX end-to-end.
- **Acceptance**: User opens one DOCX; confirms the page sequence reconstructs the journey; or files a follow-up `audit` item if it doesn't.

## BL-003 — done — Cover the sidebar Login link

- **Type**: test
- **Priority**: P1
- **Status**: done
- **Source**: session-YYYY-MM-DD
- **Description**: The sidebar Login link (logged-out state) had no test; a new scenario closes the gap. Landed in `main` `<sha>`.
```

The exact rendering can wobble (a single big table for all items is fine for short backlogs; the H2-per-item form scales better); the **fields and IDs
must be stable**.

### Other on-disk forms

Same schema, different storage:

- **Jira** — map `type` → Issue Type, `priority` → Priority, `status` → Status, `source` → custom field or labels, `acceptance` → Acceptance Criteria.
- **GitHub Issues** — map `type` and `priority` to labels (`type:fix`, `priority:P1`), `status` to open/closed + labels, `source` to a line in the
  body, `acceptance` to a checklist in the body.
- **Confluence** — one row per item in a single table page; columns match the schema.
- **JSON / CSV** — one object/row per item, fields as keys/columns.

When the user's project uses one of these, ingest and emit in that shape; don't force a Markdown file alongside.

## Mode A — Generate

Build a candidate backlog by scanning the project state. The scanning sources, in order:

### Sources to scan

| Source                                       | How                                                                                                                                                                                                                                       |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Code TODO / FIXME / XXX / HACK comments      | `grep -rnE "TODO\|FIXME\|XXX\|HACK" --include='*.py' --include='*.md' --include='*.yml' .` from the repo root                                                                                                                             |
| The gap inventory entries                    | Each entry is a candidate. Most are _the SUT's_ work, not ours — mark them `type: doc` (we document) unless we have an actionable fix on our side. When in doubt: file as `priority: P3`, `description` notes "informational — SUT-side". |
| The FRD's hardening recommendations          | Same logic — informational. Surface only if the user wants them in the backlog.                                                                                                                                                           |
| Skills written but never run                 | `find skills -name SKILL.md` and check whether any audit/review skill has output evidence anywhere. If not, file an `audit` item.                                                                                                         |
| Release-hardening items the session surfaced | From the conversation history, the maturity review, or anything the user/Claude flagged as "later" / "follow-up". Mark `source: session-<date>`.                                                                                          |
| Pending PR follow-ups                        | If a recent PR's description carries a `[ ] pending` item in the Test plan (e.g. "manual e2e workflow run"), it's a candidate.                                                                                                            |

### Procedure (Generate)

1. **Run the scans.** Print a short summary per source — N TODOs found, M gap-inventory entries, K skills awaiting first run, etc.
2. **Read existing backlog** (if any) to learn the highest `BL-NNN` and to dedup. If no backlog exists, plan to create one in whichever form the team
   uses.
3. **Build the candidate item list.** For each unique candidate not already in the backlog, draft the eight required fields. **Do not invent
   priorities silently** — assign a starting priority but flag every priority assignment as the audit's guess, to be confirmed.
4. **Surface for review.** Print the candidate items, grouped by `type`. Ask the user to:
   - Add / remove / merge / split items.
   - Confirm priorities (the audit's are guesses).
   - Confirm titles / descriptions read right.
5. **Persist on approval.** Write to the canonical backlog. Append new items, leaving existing ones untouched. Never reorder or rewrite existing items
   without a separate explicit ask.
6. **Stop.** Do not start working on items. Do not file GitHub issues. Do not push.

## Mode B — Ingest

Take an existing backlog and normalise it into the schema, then merge with the canonical backlog. The source can be anything — Claude is multi-modal.

### Input forms

| Form                  | How                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| Paste in chat         | User dumps lines / a list / a markdown fragment. Parse into items.                             |
| File path             | User points at `path/to/backlog.md` or similar. Read it.                                       |
| GitHub issues         | `gh issue list --state open --limit 100 --json number,title,body,labels` for the current repo. |
| Jira export           | CSV/JSON from Jira; read it; ask which columns map to which schema field if ambiguous.         |
| Confluence page       | Paste the rendered page, or export to HTML/PDF and read it.                                    |
| PDF / image           | Read directly (multi-modal); extract items by structure.                                       |
| Other tracker exports | CSV, JSON, Markdown — read it; ask for the column-to-field mapping if ambiguous.               |

### Procedure (Ingest)

1. **Read the input.** Print a short summary: N raw items found.
2. **Normalise each raw item** to the schema. Where a field can't be inferred (priority, type, acceptance), mark `<TBD>` rather than guessing. Drop
   blank fields entirely if optional.
3. **Read existing backlog** to dedup. For each incoming item, find candidates in the existing backlog by title-similarity (close enough is "same
   item"); list them as `(possible dup of BL-NNN)` rather than skipping silently.
4. **Surface for review.** Print the normalised items, marking `<TBD>` fields and dup candidates explicitly. Ask the user to:
   - Fill `<TBD>` fields.
   - Confirm dedup decisions (merge / keep both / drop).
   - Adjust normalisation where the auto-pass got it wrong.
5. **Persist on approval.** Append accepted items to the canonical backlog, assigning IDs from the next available `BL-NNN`. Update existing items only
   if the user explicitly maps an incoming item onto one.
6. **Stop.**

## Editing the backlog directly

If the user is editing an item by hand (changing status to `done`, bumping priority, adding `acceptance`), do not run the skill — they can edit the
file (or the Jira ticket, or the issue). The skill is for _adding_ items in bulk (generate / ingest) and for _normalising_ incoming data, not for
routine status flips.

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

### Generate — gap-inventory entry

A gap-inventory entry like `<entry-ref> — Chrome restores no-store authenticated pages from BFcache.` with a recommendation in the entry (e.g. send
`Clear-Site-Data: "cache", "cookies"` on the logout response). That's SUT-side; not our backlog. The audit surfaces it as **informational** with
`priority: P3`, `type: doc`, description "informational — SUT-side hardening recommendation; covered by the cross-browser red tests on our side."

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
- **Description**: From user paste. Needs clarification — placeholder gap from the FRD, or a regression?

## BL-NNN — Add Safari to the CI matrix

- **Type**: feat
- **Priority**: <TBD>
- **Status**: open
- **Source**: paste, session-<date>
- **Description**: Currently the matrix is Firefox + Chrome. Safari requires `safaridriver` (macOS-only runners). Cost/benefit tradeoff worth raising.
```

The `<TBD>`s are surfaced to the user; nothing is invented.

### Ingest — Jira export

User exports a Jira filter to CSV; the skill reads it. Per-row mapping (typical):

- Jira `Summary` → `title`
- Jira `Issue Type` → `type` (`Bug` → `fix`, `Story` → `feat`, etc. — surface the mapping for the user to confirm).
- Jira `Priority` → `priority` (`Blocker` → `P0`, `Critical/Highest` → `P0`, `High` → `P1`, …).
- Jira `Status` → `status` (`To Do` → `open`, `In Progress` → `in-progress`, `Done` → `done`).
- Jira `Issue Key` → `source` (e.g. `JIRA-1234`) and keep as the `id` if the project uses Jira IDs as canonical.

Same flow as the paste form: normalise, surface, persist on approval.

## When to run this skill

- The user asks: "draft the backlog", "refresh the backlog", "what's still open", "list follow-ups", "import these issues", "ingest this list".
- After a major milestone (a release-candidate cut, a big merge series) — capture what was left for next round.
- When a fresh paste lands in chat that looks like backlog material.
- When the user points at a Jira filter, a Confluence page, a PDF export, or a CSV — multi-modal ingest is the same workflow.

## What this skill does NOT do

- It does not start _working_ on backlog items. The skill files and normalises; it does not implement.
- It does not push items to GitHub issues (unless the user explicitly asks).
- It does not silently rewrite existing items in the canonical backlog. Existing items are mutated only on explicit user request.
- It does not guess priorities silently. Every guess is flagged for confirmation.
- It does not enforce one storage form. `BACKLOG.md`, Jira, Confluence, GitHub issues, JSON — the schema is the same; the on-disk form follows the
  team's existing convention.
