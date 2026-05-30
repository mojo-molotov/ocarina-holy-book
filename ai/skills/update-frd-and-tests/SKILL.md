---
name: update-frd-and-tests
description:
  Workflow for updating an item in the FRD (a requirement, a known-bug entry, an element ID, a business rule) and propagating the change to every
  affected POM, connector, scenario, the test-strategy doc, and the gap inventory — verifying empirically before writing any new assertion, and never
  silently flipping a gap test green when the SUT appears to have fixed something. **The "FRD" here is the project-internal artifact carried by the
  automated-tests repository** (the local file the suite reads as its source of truth — typically a Markdown file like `CURA_FRD.md`); this skill
  never reaches into upstream systems (Confluence, Jira, an external OpenAPI registry, a PDF in a SharePoint) — those are read-only sources the
  internal FRD may be derived from, edited by their own owners. Plan first, surface for review (the changes are authoring data), then apply per the
  user's sign-off. Use whenever the user asks to update the project's internal spec copy, amend a requirement in it, mark a gap resolved, change an
  element ID, or adapt tests after a SUT spec change. Never auto-apply; never "fix" a gap test to green without explicit gap-resolution evidence and a
  spec + gap-inventory update.
---

# Update a spec item and adapt the affected tests

A workflow skill for when the spec changes — either because the user is amending a requirement, or because the SUT's actual behaviour drifted from
what the spec asserts and the spec needs to catch up. The skill walks the change end-to-end: spec → empirical verification → affected artifacts →
proposed updates → review → apply → strategy/gaps reconciliation.

The discipline:

- **The FRD is the project-internal spec artifact.** The file lives _in this repository_ (typically Markdown, e.g. `CURA_FRD.md`); it is the suite's
  source of truth and the only thing this skill writes to. Upstream artifacts — a Confluence page, a Jira epic, an external OpenAPI registry, a PDF in
  SharePoint — are read-only sources for the internal FRD; they are **never** edited by this skill, and the user is responsible for updating them
  out-of-band through their own ownership channels. Update the internal FRD first, deliberately, with a one-sentence reason for the change.
- **Verify empirically before adapting any assertion.** Don't rewrite a test against the new claim until a probe / source read / live HTML confirms
  it.
- **Never silently flip a gap test to green.** If the spec change marks a gap as resolved, the corresponding intentional-fail test does **not**
  disappear — it stays as a regression guard, reframed from "intentional fail" to "passing test". The user signs off on this transition explicitly.
- **Authoring data needs review.** Every proposed change to a POM selector, connector, scenario assertion, or strategy entry is surfaced as a plan
  before any file is touched (per `CLAUDE.md` → "Datasets are authoring decisions").

Default targets: the FRD, the test-strategy doc, the gap inventory, `src/`. For a different repo, ask the user.

## Procedure

### Step 1 — State the change in one sentence

"REQ-AUTH-2 now requires the session cookie to be expired on logout, not just the server-side session destroyed (SUT fixed the corresponding gap in
deployment Y)." Or: "REQ-APPT-3 visit-date input ID renamed from `txt_visit_date` to `txt-visit-date`." Or: "The past-date booking gap is resolved —
the SUT now rejects past dates server-side."

The one-sentence form forces clarity. Bigger changes split into multiple invocations.

### Step 2 — Update the spec entry

Apply the change to the relevant section of **the project-internal FRD file in this repository** — the requirement definition, the known-bug entry,
the element ID in the form table, the business rule. Add a one-line revision note in the doc's revision history (if it has one — most should).

This is the project's copy of the spec moving. Apply it before touching tests. The tests adapt to the spec, not the other way around.

If the upstream source-of-truth (Confluence, Jira, an external OpenAPI registry, a PDF) also needs to change to stay coherent, **surface that as a
follow-up the user owns** — name the upstream artifact and what should change there, then stop. This skill does not write to upstream systems.

### Step 3 — Empirically verify the new claim

Per the `empiricism` skill: every load-bearing claim in the new spec entry must come from observation, not assumption. Pick a verification path:

- **SUT source read** — when the source is accessible (open source or you own it). Backend-stack dependent:
  `gh api repos/<org>/<repo>/contents/<file>.php` for a PHP backend; clone the repo for Node/Java/Go/Ruby; read the OpenAPI / GraphQL schema for a
  closed-source SUT.
- **Live HTML read** — a throwaway probe that captures `outerHTML` for the affected element/page.
- **Cookies / headers** — a `curl -v` probe for session lifecycle.
- **End-to-end probe** — drive the exact flow and observe.

Record the empirical answer in the spec entry itself (a line like "verified against the deployed app on YYYY-MM-DD: cookie expiry observed via
`driver.get_cookies()` post-logout"). The probe is throwaway; the _finding_ lives in the spec.

If verification fails or is indeterminate, stop. Don't propagate a claim you couldn't confirm.

### Step 4 — Find every artifact the change touches

Grep for the changed REQ ID, element ID, business-rule keyword, and the symbols those imply:

```bash
# Element ID change — find selectors using it
grep -rn "txt_visit_date" src
grep -rn "txt-visit-date" src

# REQ change — find scenarios / strategy entries referencing it
grep -rn "REQ-AUTH-2" .
grep -rn "<known-bug-id>" .

# Gap resolved — find the corresponding intentional-fail test
grep -rn "name=\".*Past date booking" src/tests/scenarios

# Selector text changed — find locators
grep -rn "No appointment\." src/pages
```

Build the affected-artifacts list:

| Artifact class    | Where to look                                                                                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| POM selectors     | `src/pages/**/*.py` — `_xxx = (By.…, "...")` lines                                                                                                      |
| POM method bodies | `src/pages/**/*.py` — any element access mentioning it (Selenium `find_element` / `execute_script`; Playwright `page.locator(...)` via `driver.submit`) |
| Connectors        | `src/lib/connectors/test_steps/**/*.py` — methods wrapping affected POM operations                                                                      |
| Scenarios         | `src/tests/scenarios/**/*.py` — flows asserting against the changed surface                                                                             |
| Datasets          | `src/tests/scenarios/**/datasets/**/*.py`, inline `*_cases` tuples                                                                                      |
| Strategy doc      | Coverage tables, the suite/campaign tree, expected outcome categories, known-gaps section                                                               |
| Gap inventory     | Entries citing the changed area                                                                                                                         |

Classify each hit:

- **Affected** — the change requires editing this hit.
- **Incidental** — the hit mentions the changed area but the test isn't asserting on the changed surface. Don't touch.

### Step 5 — Special handling for gap resolution

If the spec change is **"the SUT fixed a gap" / "this known-bug entry is resolved"**, the intentional-fail test against that gap is special:

1. **Do not delete it.** It stays as a regression guard.
2. **Do not silently flip its assertions.** A flipped assertion that passes for the wrong reason (e.g. a transport flake mimicking rejection) is
   exactly the trap the original misdiagnosis-prevention rules guard against.
3. **Walk the resolution evidence with the user.** Did the SUT actually fix it? When was the fix observed? Is the fix server-side,
   deployment-specific, or behind a feature flag?
4. If the resolution is confirmed:
   - **Reframe the test** — change the assertion from "must NOT confirm" to "must confirm" (or the appropriate inversion). The test name should also
     flip: e.g. `Appointment - Past date booking accepted` → `Appointment - Past date booking rejected`. **Surface this rename for the user.**
   - **Move it in the test-strategy doc** — from the "Intentional gap fails" category to the "Pass everywhere" category. Update the coverage row's
     "Type" column from "Business logic vulnerability" / **INTENTIONAL FAIL** to "Happy path" / PASS or similar. Update the known-gaps table — remove
     the row.
   - **Update the gap inventory** — mark the entry resolved (or remove it, citing the resolution date and the PR / deployment that fixed it).
5. **If the resolution is NOT confirmed** (probe shows the gap is still real on deployment): the spec update was premature; back it out or mark
   provisional.

Same logic for documented cross-browser reds. If a browser's behaviour changed (a Chrome version stops admitting `no-store` pages to BFcache, say),
apply the same reframing path.

### Step 6 — Propose the plan

Surface, file by file, what you intend to change. Use this exact template:

```markdown
# Spec-update plan — <one-sentence change>

## Spec doc

- §<X.Y> — <before> → <after>. Reason: <one line>.
- Revision history: `| 1.N | YYYY-MM-DD | … | <change summary> |`.

## Empirical verification

- <claim 1>: <how verified — source file/line, probe finding>
- <claim 2>: …

## Affected artifacts

### POMs

- `src/pages/<file>.py:<line>` — selector / method body — <before> → <after>.

### Connectors

- `src/lib/connectors/test_steps/<file>.py:<line>` — <change>.

### Scenarios

- `src/tests/scenarios/<file>.py:<line>` — assertion / flow — <change>. Category: <pass-everywhere / intentional-fail being reframed / etc.>

### Strategy doc

- Coverage row: <before> → <after>.
- Category: <move / unchanged>.
- Known-gaps: <remove row / add row / unchanged>.

### Gap inventory

- §<entry>: <mark resolved / remove / amend>.

## Reframings (gap tests changing status)

- `<test name>` — was Intentional FAIL (`<known-bug-id>`). Now: <happy path / new framing / removed?>.
  - Resolution evidence: <link to probe finding>.
  - Proposed rename: `<old name>` → `<new name>`.
```

Print the plan. Wait for the user's go.

### Step 7 — Apply approved changes

Once the user signs off:

1. Apply FRD updates first.
2. Apply POM / connector / scenario updates.
3. Apply strategy doc and gap-inventory updates.
4. Run `ruff format && ruff check && mypy` — clean any fallout.
5. Run the affected scenarios on both browsers. The outcome should match the new expected category (the reframed gap test now passes; pass-everywhere
   tests still pass; etc.).

Do not commit. Surface the diff to the user — they commit when ready (or invoke the `pr-report` skill).

### Step 8 — Stop

Do not iterate without the user. Do not "go on" to neighbouring changes the audit happens to spot. One spec change at a time.

## What this skill never does

- **It never writes to upstream spec systems.** Confluence pages, Jira tickets/epics, external OpenAPI registries, SharePoint PDFs — these are
  read-only here. The scope is the project-internal FRD artifact in this repository. If the upstream needs to change too, surface that as a follow-up
  the user owns and stop.
- It never flips an intentional-fail test to green without explicit resolution evidence and the full reframing pass (spec, gap inventory, strategy,
  test rename).
- It never deletes a test that was previously an intentional-fail gap test. They stay as regression guards, reframed.
- It never silently propagates a SUT-side change. The spec update is deliberate and visible.
- It never invents an empirical answer. If verification is indeterminate, the workflow stops.
- It never updates the strategy doc's pass/fail counts — there are none (per the "no totals" rule). It updates _categories_.

## When to run this skill

- The user announces a SUT spec change ("the SUT fixed past-date validation in deployment X", "the appointment form's date input was renamed").
- The user is amending the FRD by hand and wants the tests pulled along.
- A `review-suite-stability` audit surfaced a _surprise green_ on a gap test that, on investigation, is real (not environmental contention) — that's
  the entry point for resolving the gap.
- A gap-inventory entry needs to be marked resolved.

## What this skill does NOT do

- It does not invent spec content. The one-sentence statement of the change comes from the user.
- It does not write new tests for fresh requirements. Use `extend-coverage` to find adjacent gaps, then `empiricism` to author them.
- It does not run the full suite preemptively — affected scenarios only, on both browsers, after the user signs off on the plan.
- It does not commit or push. That's the `pr-report` skill + the user's call.
