---
name: business-attack-ideation
description:
  "**Adopt a black-hat lens** to brainstorm *business attacks* on the SUT — not spec-clarity questions, not coverage gaps, but the ways a
  malicious-but-legitimate user could weaponise the product's normal flows to cause harm: saturation booking that blocks the appointment service for
  real patients, repeated submissions that exhaust a shared resource, slot-hoarding that denies access to legitimate consumers, identifier-recycling
  that confuses the audit trail, off-hours mass-actions that overwhelm staff. The attack is **business-shaped, not technical** — every step is a thing
  a real user *could* do through the normal UI. The harm is **second-order** — humans can't work, consumers can't consume, the service degrades.
  Generates a list of attack scenarios with their business-impact narrative, the test shape that would observe whether the SUT is robust against each,
  and the hard line between scenarios that are appropriate to encode as functional tests (saturation-shaped, all legitimate inputs) versus scenarios
  that cross into active-security territory and are **out of scope** for this suite. Use whenever the user asks to think like an attacker, brainstorm
  business attacks, find ways to abuse the product through legitimate means, or extend coverage with adversarial-but-realistic flows."
---

# Business-attack ideation — abuse the product without breaking the rules

A black-hat ideation skill. Spec-clarity reviews (`review-spec-gaps`) ask _what's unclear_. Coverage extensions (`extend-coverage`) ask _what isn't
tested adjacent to existing flows_. This skill asks a different question:

> _If I were a determined, legitimate-credentials user who wanted to harm the product or its users, what would I do?_

The answer is never "inject SQL", never "fuzz the auth endpoint", never "scan for CVEs". Those are **active security testing** and are out of scope —
the project's hard rule is in `CLAUDE.md` ("Security testing is functional and static — never active"). The answer is _always_ a business flow
exercised in a way the designer didn't anticipate: lots of bookings, well-timed bookings, weirdly-spread bookings, bookings that look like noise but
aren't.

The output is a **scenario catalogue** with business-impact narratives — the user picks which to encode as functional tests (e.g. the existing
`saturation_booking` test is a canonical encoding of this skill's first scenario) and which to leave as static analysis only.

## The line — what's in scope, what isn't

In scope (functional encoding allowed):

- **The user does many of a normal thing.** N bookings, N logins, N page views — each one a legitimate action, the aggregate harmful.
- **The user does a normal thing at a bad moment.** A booking right before close, a logout right before form submit, a back-button at a redirect.
- **The user does a normal thing with extreme but valid inputs.** A visit date at the legal maximum, a name at the maximum length, a comment field
  filled to capacity.
- **The user does normal things in a surprising order.** Logout-then-back-button (already a documented finding, §B-BROWSER-1). Book-then-immediately-
  book-again. Confirm-then-confirm-again.
- **The user creates state that other users have to live with.** A booking on a popular slot. A profile with a name that collides with another user's
  display name (if such a thing is possible in CURA's data model — verify per `empiricism`).

Out of scope (do not encode, do not even sketch as a probe):

- **Injection-shaped payloads.** `'; DROP TABLE …`, `<script>alert(1)</script>`, path traversal strings. Even in static description.
- **Auth bypass.** Forged tokens, replay attacks, fixed-session reuse.
- **Mass-scale request flooding.** Anything that hits the SUT at HTTP-rate rather than UI-rate.
- **Side-channel attacks.** Timing oracles, cache probing, error-message scraping.
- **Anything targeting infrastructure rather than the business flow.** A scenario that exploits Heroku's eco dyno limits as the attack vector belongs
  in `IDENTIFIED_GAPS.md §A-ENV-*`, not here.

The line is sharp: **the action is one a legitimate user could take through the UI, the harm is to the business, the test is functional.**

## The eight attack archetypes

For ideation, walk these archetypes against the SUT. CURA-specific examples for each — adapt the archetype to any SUT.

### 1. Saturation

The user performs many of a normal action to exhaust a shared resource.

- **CURA example**: book N appointments across N legitimate future dates, leaving no slot for real patients. _Already encoded as
  `saturation_booking`._
- **Test shape**: loop N iterations of the booking flow, then verify (or simply _observe_ — the audit might be informational rather than assertive)
  the system's state.
- **Business impact**: real patients can't book; staff has to manually clean up; trust in the system erodes.

### 2. Slot-hoarding (denial via legitimate occupancy)

A variant of saturation: the user occupies high-value slots that other users want. The action is legitimate (a booking _is_ allowed), the aggregate
denies access.

- **CURA example**: book every Monday-morning slot for the next year. Each booking is a real, allowed action; the aggregate is a denial.
- **Test shape**: book a _pattern_ of slots (every X day at Y time), then observe whether the system enforces any anti-hoarding rule (booking limits
  per user, time-windowed quotas).

### 3. Off-hours mass action

The user performs many actions when staff is least equipped to respond.

- **CURA example**: book 200 appointments at 03:00 local. Staff arriving at 09:00 face a triage queue.
- **Test shape**: timestamp-controlled booking burst at a time the SUT might rate-limit or might not. Observe.

### 4. Repeated identical action (idempotency abuse)

The user repeats the same action to test the SUT's deduplication behaviour. If the SUT accepts duplicates, the user creates noise; if the SUT rejects
duplicates, the user has confirmed the deduplication rule and may pivot.

- **CURA example**: click "Book" 5 times in rapid succession on the same form. Each submit is a legitimate POST; the SUT's response is the audit.
- **Test shape**: dispatcher-style rapid resubmit (cross-ref `review-submit-dispatchers`).
- **Business impact**: a single user creates the workload of 5; calendars contain duplicates that staff has to reconcile.

### 5. Boundary-value abuse

The user submits inputs that are _valid_ but at the extreme — the edges the designer probably tested once and forgot about.

- **CURA example**: book a visit date 50 years in the future. Submit a maximum-length comment field. Both are valid per the form's input contract.
- **Test shape**: data-driven test with boundary values.
- **Business impact**: stale future bookings clutter the schedule indefinitely; oversized comments stress UI rendering downstream.

### 6. State-leak across users (data hygiene attack)

The user creates state visible to other users via the SUT's shared surfaces.

- **CURA example**: the demo account is shared in this testbed (a documented project quirk). A user who creates a booking and doesn't clean it up
  affects every other user of the same account. In a real SUT, the equivalent would be a profile picture, a public review, a shared resource.
- **Test shape**: create state, switch identity, observe whether the state is visible / persistent / removable.
- **Business impact**: privacy leak, audit-trail confusion, support burden.

### 7. Surprising-order operation chain

The user performs a sequence of legitimate operations in an order the designer didn't model.

- **CURA example**: book → start logout → cancel logout → continue editing. Or: open form in tab A, log out in tab B, submit in tab A.
- **Test shape**: multi-step scenario with the order intentionally adversarial.
- **Business impact**: ambiguous final state, potential phantom bookings, audit-trail gaps.

### 8. Identity-collision / impersonation-shaped (legitimate side)

The user picks an identity choice that collides with another user's identifying field — without actually impersonating, just creating ambiguity.

- **CURA example**: choose a display name identical to another active user. (Verify whether CURA's data model allows this before encoding — per
  `empiricism`.)
- **Test shape**: create the colliding identity through the normal signup / profile flow.
- **Business impact**: staff confuses two users, sends one's appointment to the other, etc.

Note: **this is not impersonation, not auth-bypass, not credential theft**. It's exploiting the _display_ / _identification_ model. If the SUT lets
you do it through the UI, it's a business flaw worth surfacing.

## Procedure

### Step 1 — Anchor on the SUT's business model

Read enough of `CURA_FRD.md` to know what the SUT _does_ commercially (CURA: appointment booking + medical-history records for a demo clinic). The
attack archetypes attach to _what the business loses if exploited_ — without anchoring on that, the ideation drifts into technical attacks.

### Step 2 — Walk the eight archetypes against the SUT

For each archetype, ask:

- Is there a CURA flow this maps onto?
- Is the action _legitimate_ via the normal UI (no protocol-level tricks)?
- Is the harm _business-shaped_ (humans can't work, consumers can't consume, trust erodes)?
- Has anyone already encoded this? (Check the existing scenario set — `saturation_booking` is the canonical first.)

If yes to all four: candidate scenario. If no to legitimacy or harm-shape: drop.

### Step 3 — Cross-check against existing artifacts

For each candidate:

- Is it already in the suite? — silent (don't re-propose).
- Is it already documented in `IDENTIFIED_GAPS.md`? — cross-reference, don't duplicate.
- Is it adjacent to a documented gap? — note the relationship.

### Step 4 — Cross-check against the hard line

For each candidate, the kill question: _would encoding this require injection-shaped inputs, auth bypass, request flooding at the HTTP layer, or any
attack on infrastructure rather than business flow?_ If yes → **out of scope**. Mark as static-analysis-only or drop entirely.

### Step 5 — Surface the catalogue

```markdown
# Business-attack catalogue — `<SUT>` (<date>)

## In-scope attack scenarios (functional encoding appropriate)

### Saturation

- **Scenario**: <one-sentence description>.
- **Action shape**: <what the user does, all legitimate>.
- **Business impact**: <who loses, how>.
- **Test shape (suggested)**: <high-level: loop count, dispatcher use, observation vs assertion>.
- **Cross-reference**: already encoded as `<test name>` | candidate for `extend-coverage`.

### Slot-hoarding

- **Scenario**: …
- … (one block per scenario)

### (...)

## Out-of-scope (active-security territory; not encoded)

- <Description, why out of scope>. Filed only as a static note, not as a test.

## Cross-references

- Existing scenarios in suite: <list>.
- `IDENTIFIED_GAPS.md` §<refs> with adjacent shape.
- `CURA_FRD.md` §<refs> describing the targeted flows.

## Recommended next motions

- For each in-scope scenario: <encode via `extend-coverage` | `empiricism` to verify the flow first | discuss with stakeholders before encoding>.
- For each out-of-scope scenario: no test motion. Note in a discussion artifact if the team wants to track it.

## Verdict

<one-line: N in-scope candidates, K already covered, J out of scope, nothing material>.
```

Print the catalogue.

### Step 6 — Stop. The user decides.

Each in-scope candidate can resolve as:

- **Encode** — invoke `extend-coverage` to author the test (with `empiricism` to verify any SUT-behaviour assumption first).
- **Defer** — interesting but not this release.
- **Discuss** — the scenario has business / stakeholder dimensions that need a conversation before coding.

Out-of-scope candidates have no follow-up motion. They're noted; the suite doesn't encode them.

## Hard rules

- **Every action is one a legitimate user could take through the UI.** If the scenario requires a curl flood, a raw POST, a forged token, or any
  protocol-level trick, it's out of scope.
- **The harm is business-shaped, not technical.** "The server returns 500" is not the harm; "staff can't process today's appointments" is the harm.
- **Per `CLAUDE.md`: security testing is functional and static — never active.** This skill respects the line. Even ideation that crosses the line
  gets dropped, not preserved-as-static.
- **Don't sketch attack-shape payloads.** A SQL-injection example is out, even as illustration.
- **Saturation done through the UI is functional.** Saturation done through raw HTTP is not. The same idea on the two sides of the line is in scope on
  one and out on the other.
- **Cross-reference the existing suite.** Don't re-propose what `saturation_booking` already covers.
- **Verify SUT-behaviour assumptions before encoding.** A scenario based on "I think CURA allows duplicate bookings" needs the `empiricism` motion
  first.

## When to run this skill

- Coverage planning sessions — what hostile-but-realistic flows are we missing?
- After a real-world incident pattern in the user's industry (medical scheduling abuse, restaurant-reservation no-show waves) — does our SUT have the
  equivalent surface?
- Before a release — is the suite robust against the "many users doing slightly-weird things" model, not just the happy-path user?
- During stakeholder review — surface the catalogue as a discussion artifact for product / legal / compliance to weigh in.

## What this skill does NOT do

- It does not encode the tests. Use `extend-coverage` / `empiricism` after the user picks scenarios.
- It does not verify SUT behaviour. Use `empiricism` / `write-a-probe` for that.
- It does not propose injection, fuzzing, brute-force, or active-security techniques. Out of scope, by project rule.
- It does not file `IDENTIFIED_GAPS.md` entries. Cross-references are recommended; entries are a follow-up via `update-frd-and-tests`.
- It does not produce attack payloads. Even illustrative ones.
- It does not run anything against a real or demo SUT. Static ideation only.
