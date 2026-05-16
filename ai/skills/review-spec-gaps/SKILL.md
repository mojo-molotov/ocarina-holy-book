---
name: review-spec-gaps
description: Read the project's specs (the FRD first, the test-strategy doc as a cross-check) the way a QA Analyst would in a static review and surface **areas of misunderstanding** — places where the spec doesn't quite say what happens, what the boundary is, what the user sees, or how things compose. The tone is **benevolent and curious**, never accusatory: the deliverable is a list of *questions a careful reader would ask*, not a catalogue of "flaws". A spec gap is rarely "the spec is wrong" — it's almost always "the spec didn't anticipate this dimension". Use whenever the user asks to review the specs, do a static analysis pass, identify ambiguities, find clarification questions, prepare for a stakeholder review, or harden the FRD before a release. Surface questions; never silently fill them in.
---

# Review — spec gaps, the QA-Analyst way

A static-review skill. Read the FRD (primary) and the test-strategy doc (cross-check) and surface **areas of misunderstanding** — the questions a
careful QA Analyst would write in the margin of a spec walkthrough.

**Tone.** Benevolent. Curious. Never accusatory. The deliverable is a list of clarification questions, not a list of "flaws". Phrasings that work:

- _"What happens when …?"_
- _"How does the system behave if …?"_
- _"Is it specified what the user sees when …?"_
- _"The spec mentions A but doesn't say what happens to B."_
- _"This rule is clear; the boundary isn't."_

Phrasings to **avoid**:

- ~~"This is a flaw in the spec."~~
- ~~"The spec is broken."~~
- ~~"You forgot to specify …"~~
- ~~"This is wrong."~~

A spec gap is rarely "the spec is wrong". It is almost always "the spec didn't anticipate this dimension yet". The skill surfaces the dimension; the
human picks whether to extend, defer, or scope out.

**Default target:** the FRD. Cross-reference the test-strategy doc and the gap inventory to avoid surfacing questions that are already documented
elsewhere.

**This is a static review.** No probes. No live-app observation. No assertions about the SUT's actual behaviour. The skill asks _"is this clear from
the document?"_ — not _"is the document right?"_.

## Categories of question to walk

These are the dimensions a QA Analyst checks. For each, the audit re-reads the spec asking _"is this dimension covered?"_. If yes — silent. If not, or
fuzzy — surface a benevolent question.

### 1. Edge-case behaviour

For each requirement that describes a flow, ask:

- What happens at the boundary inputs (empty, minimum, maximum, special characters within the user's plausible set)?
- What happens when the user does an action _out of order_ (skips a step, repeats a step)?
- What happens at the boundary of permissions (just-authenticated, just-logged-out, session-about-to-expire)?

Example question (illustrated against <https://github.com/mojo-molotov/ocarina-with-ai-example>): _"REQ-AUTH-1 covers login with valid and invalid
credentials. What happens when the username contains trailing whitespace? Is that a separate rejection path or treated as the empty case?"_

### 2. Boundary definitions

For each business rule that has a numeric or categorical boundary, ask whether the boundary is _defined_:

- A date validation: how far in the future is "future"? Is today valid?
- A textual field: is there a minimum / maximum length? An allowed character set?
- A count: how many of X are allowed?

Example question: _"REQ-APPT-2 (worked example) says a visit date is required. The boundary isn't defined: is today a valid visit date, or is the
minimum tomorrow? Is there a maximum (a year out, a decade)?"_

### 3. Failure behaviour

For each happy-path requirement, ask what the spec says happens when the path fails:

- What error message does the user see? In which language? At which precision?
- Does the form re-display with the inputs preserved, or cleared?
- Does the failure log on the server side? Visibly to the user?
- Is the failure recoverable in the same session, or does it require a re-login?

Example question: _"REQ-APPT-3 (worked example: booking) describes the success path. If the submission fails, is the user shown a specific error,
returned to the form with values preserved, or sent elsewhere?"_

### 4. Visual / UX feedback

For each interaction, ask whether the _user-visible_ feedback is specified:

- Loading states (spinner? disabled button? text change?).
- Confirmation states (toast? page change? inline message?).
- Empty states (e.g. in the worked example, already covered by REQ-HIST-4).
- Hover, focus, error styling.

Example question (worked example): _"REQ-AUTH-1 says 'Login failed!' is displayed on bad credentials. Is the error displayed inline, as a toast, on a
redirect? Is the username preserved in the form after the failure?"_

### 5. State coverage

For each page, ask whether the spec covers every state the user can land in:

- Logged in / logged out.
- Empty / populated.
- After a failed action.
- During / after a redirect.
- After back-button navigation.
- After tab close and reopen.

Example question (worked example): _"REQ-HIST-3 says history renders most-recent-first. Does the spec define what history shows immediately after a
fresh login (no bookings yet, before any session activity)?"_ (For this worked example: yes — REQ-HIST-4. Don't flag.)

### 6. Data validation rules

For each input field, ask:

- Is the validation client-side, server-side, or both?
- What does the server do with malformed input?
- Are there input-type constraints (a date input vs. a free-text field)?

Example question (worked example): _"REQ-APPT-2 names `visit_date` as required. The validation strategy (client-side only? server-side? both?) isn't
stated. The corresponding gap entry tells us empirically that server-side validation is missing — should the spec define what the server **should**
do, even if the gap inventory reports the SUT doesn't?"_

### 7. Cross-feature interactions

For each requirement that mentions another feature, ask whether the interaction is specified:

- Logout while a form is partially filled — is the form data lost? Confirmation prompt?
- Two browser tabs both logged in as the same user — supported? Undefined?
- The same operation on different pages where it's reachable.

Example question (worked example): _"REQ-AUTH-2 (session management) and REQ-APPT-3 (booking) both exist; how should the system behave if the session
expires mid-form-fill? Is this defined, or does it fall back to whatever the framework does?"_

### 8. Ambiguous wording

For each requirement, ask whether each word that _could_ be interpreted multiple ways is anchored:

- "The system validates the input" — validates how, against what?
- "The user can log in" — only the demo user, or any user?
- "The page displays the appointment" — which fields? In which order?

Example question (worked example): _"REQ-AUTH-1 says authentication is 'case-sensitive'. The spec confirms this for the username and password. Is
whitespace sensitivity also defined? (The coverage table tests `lowercase` and `uppercase` cases; whitespace doesn't appear.)"_

### 9. Inferred-from-app, not-documented

When the FRD describes a behaviour that the test suite clearly relies on but the spec doesn't _state_ (you have to read the codebase or run the app to
know), ask whether that behaviour should be in the spec:

- Inferred element IDs (when the FRD documents these well, less of a gap; flag only when they're inferred from the code).
- Inferred order of operations.
- Inferred default values.

Example question (worked example): _"The visit-date input uses `dd/mm/yyyy` per the form-table section. Is the date format defined as a requirement,
or inferred from the input? If a user pastes `2026-05-15`, what does the system do?"_

## Procedure

### 1. Read both docs once, top to bottom

```bash
cat <path-to-FRD>
cat <path-to-test-strategy-doc>
```

Don't note questions on the first read — just absorb. A QA Analyst doing static review reads first; the questions surface on the second pass.

### 2. Walk each requirement and known-bug entry against the nine categories

For each requirement section, ask the nine questions. Filter:

- **Specified** (silent) — the requirement covers this dimension.
- **Documented elsewhere** (silent) — the dimension is in the test-strategy doc, the gap inventory, or the spec's known-bugs section. Don't
  double-surface.
- **Open question** — the dimension isn't covered and isn't obviously out of scope. Surface as a benevolent question.

### 3. Cross-check with the test strategy

Some questions are answered by the strategy doc rather than the FRD. If the strategy explicitly scopes out a dimension ("performance is out of
scope"), don't flag adjacent performance questions.

### 4. Surface — produce the question list

Use this exact template. **Note the phrasing throughout.**

Sample (illustrated against <https://github.com/mojo-molotov/ocarina-with-ai-example>):

```markdown
# Spec-clarity review — <spec-doc title> (+ strategy cross-check)

## Open questions

### Authentication

- **REQ-AUTH-1 — username whitespace handling.** The spec covers case sensitivity (lowercase/uppercase rejected). Whitespace (leading, trailing,
  doubled-internal) isn't specified — copy-paste from a password manager often leaves trailing whitespace. _Is whitespace treated as the empty case,
  as a separate rejection, or as significant content (stripped or not)?_

- **REQ-AUTH-1 — error display details.** The "Login failed!" message is named, but the spec doesn't say whether it's inline, toast, or page-redirect;
  nor whether the username field retains its value across the rejection. _Where on the page does the error appear, and is the username preserved?_

### Appointment booking

- **REQ-APPT-2 — visit-date boundary.** The date is required; the upper / lower bound isn't defined. The past-date gap notes that past dates are
  currently accepted, which suggests the **intended** lower bound is "today or later", but the spec doesn't state it directly. _What is the intended
  minimum and maximum visit date?_

- **REQ-APPT-3 — date format on paste.** The form table shows `dd/mm/yyyy`. _If a user pastes `2026-05-15` (ISO-format), does the datepicker accept,
  reject silently, or surface an error? Is the format an intended-strict contract or a display convention?_

### History

- (nothing open — the REQ-HIST-\* set covers the states well; the history-order gap is documented)

### Profile

- **REQ-PROF-1 — content of the empty profile.** The profile-placeholder gap entry says the profile is a placeholder with no editable fields. _Is the
  placeholder intentional and stable (a documented empty surface), or a known incomplete feature that the FRD should call out as "not yet built"?_

### Cross-feature

- **Session-expiry mid-form.** REQ-AUTH-2 covers session management; REQ-APPT-3 covers the appointment form. _If the session expires while the user is
  filling the appointment form, what's the expected experience — silent redirect on submit, mid-form warning, preservation of inputs?_

## Closed (asked, resolved by cross-reference)

- (optional — questions that came up but answered themselves on cross-check; useful to show the audit walked them)

## Summary

- Open questions: N
- Covered by other docs: M (strategy / gaps cross-references resolved them)
- Verdict: <N questions worth raising with the spec owner | nothing material to clarify>
```

Print the question list. Do not write it to a file unless the user asks.

### 5. Stop. The user decides.

Each open question can resolve in three ways:

- **Specify** — add a sentence or two to the FRD.
- **Scope out** — explicitly mark it out of scope (in the out-of-scope section of the strategy doc, or as a note in the FRD section).
- **Defer** — leave it as an open question pending stakeholder input.

The audit doesn't pick. It surfaces.

## Tone reminders (read before writing the report)

- _"What happens when …"_ > _"You didn't define …"_.
- _"The boundary isn't stated"_ > _"This is missing"_.
- _"Is it specified that …"_ > _"You should have said …"_.
- A question ends with a question mark. Genuinely.
- If a question reads like a list of complaints, rewrite it as a list of _curiosities_ — what a careful reader would ask to be sure they understand.

## Hard filters — what this skill does NOT surface

- **the SUT's actual defects.** Those go in the gap inventory and the FRD's known-bugs section, identified by empirical observation (per
  `empiricism`). This skill is about _spec clarity_, not SUT behaviour.
- **Test coverage gaps.** Use `extend-coverage` — different skill, different target.
- **Stylistic / typographic nits.** A typo isn't a spec gap. Track via the user's hand-edit, not via this audit.
- **Out-of-scope dimensions.** If the strategy's out-of-scope section lists "performance" / "accessibility" / "payment" as out of scope, don't ask
  performance / accessibility / payment questions.
- **Anything attack-shaped.** Per `CLAUDE.md` → "Security testing is functional and static — never active". A question like _"what happens when the
  user pastes `'; DROP TABLE …`"_ is out of scope; a question like _"is whitespace handling specified?"_ is fine.

## When to run this skill

- The user asks: "review the spec", "are there gaps in the FRD?", "what's unclear", "prepare for a stakeholder review", "static spec review".
- Before invoking `update-frd-and-tests` for a bulk edit — knowing the open questions lets the author batch related clarifications.
- After a SUT spec change — the change may have introduced new ambiguities.
- Onboarding a contributor — a clarity review feeds back to the FRD.

## What this skill does NOT do

- It does not edit the FRD or the strategy doc.
- It does not run probes. (If a question really is "does the SUT do X?", reach for `empiricism` / `write-a-probe` — different motion.)
- It does not file open questions as backlog items automatically (that's `manage-backlog`).
- It does not invent answers. Indeterminate is indeterminate; the question stays a question.
