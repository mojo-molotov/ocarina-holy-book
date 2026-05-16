---
name: incoherence-attack-ideation
description:
  "**Black-hat ideation focused on *incoherent* combinations** — actions where each step is individually valid but the **set** is impossible against
  physical, biographical, or real-world constraints the SUT doesn't model. The canonical example: same person books a hotel room in Paris and one in
  Tokyo with check-in times 30 minutes apart — neither booking is illegal on its own, but the pair contradicts geography. For an appointment SUT: same
  patient at two clinics 200 km apart in overlapping windows. Same identity declared as both 25-year-old and 70-year-old on adjacent forms. Same
  insurance number registered to two different birthdates. Each step passes whatever validation the SUT runs *per-form*; the SUT has no notion of
  cross-form / cross-time / cross-space coherence, so the combination is silently accepted. Generates a catalogue of incoherence patterns with the
  business-impact narrative and the **functional** test shape that would observe whether the SUT detects them — strictly through the normal UI, no
  injection / no protocol tricks. Use whenever the user asks to find logic-incoherence attacks, brainstorm 'physically impossible but allowed'
  scenarios, audit cross-context consistency, or extend coverage with reality-violating-but-input-legal flows."
---

# Incoherence-attack ideation — each step legitimate, the set impossible

A black-hat ideation skill, sibling to `business-attack-ideation` and bound by the same hard rules. The lens here is narrower and sharper:

> _Where can a malicious user create a set of actions, each individually accepted by the SUT, whose **combination** violates a real-world constraint
> the SUT doesn't model?_

The SUT validates **per-form**. The attacker reasons **across forms / time / space / identity**. The gap between the two is the vulnerability. The
output is a catalogue of incoherence patterns and the test shape that would observe each.

## The hard line (inherited from `business-attack-ideation` and `CLAUDE.md`)

In scope:

- Every step is an action a real user can perform through the normal UI.
- Every input is a legal, non-injection value the form accepts.
- The harm is **business-shaped** (fraud, double-billing, audit-trail corruption, real-user denial).
- The detection question is _"does the SUT notice the contradiction?"_ — observable through normal browser interaction.

Out of scope:

- Forged tokens, replay attacks, protocol-level tricks. Out.
- Injection-shaped payloads. Out.
- Side-channel / timing oracle attacks. Out.
- Anything that requires raw HTTP rather than the UI. Out.

Per `CLAUDE.md` → _"Security testing is functional and static — never active"_. This skill respects the line by construction: every incoherence is
built from inputs the form will accept.

## The six incoherence dimensions

For ideation, walk these against the SUT's input model. CURA-specific examples for each — adapt to any SUT.

### 1. Temporal incoherence (same actor, overlapping times)

The actor commits to being in two places (or two states) at the same moment.

- **CURA example**: book an appointment with Dr. A at 10:00 and Dr. B at 10:00 on the same day. Each booking is legal; the patient can't be in two
  exam rooms.
- **Real-world inspiration**: same hotel guest checked in to two rooms in two cities at overlapping nights.
- **Test shape**: book A; observe whether B is rejected or silently accepted. Cross-ref `empiricism` to verify CURA's actual behaviour first.
- **Business impact**: double-booked clinical resources, no-show penalties, billing ambiguity.

### 2. Spatial incoherence (same actor, infeasible travel)

The actor commits to being in two places whose travel time exceeds the gap between actions.

- **CURA example**: book an appointment at clinic X (city A) at 10:00 and at clinic Y (city B, 300 km away) at 10:30. Geographically impossible.
- **Real-world inspiration**: same passenger boarding two flights with overlapping flight times in different airports.
- **Test shape**: requires the SUT to expose location for each booking. If CURA doesn't (verify via FRD / source), the scenario is _static analysis
  only_ — note as "SUT lacks location model; incoherence undetectable", not "SUT has a bug".
- **Business impact**: phantom bookings, fraud-shaped scheduling, audit trail breakage.

### 3. Biographical incoherence (same actor, contradictory identity facts)

The actor declares contradictory facts about themselves across forms.

- **CURA example**: register profile with birthdate 1990; later submit a form declaring age 70. Or: declare two different insurance numbers under the
  same user account, both individually valid.
- **Real-world inspiration**: same person declaring two different birth countries on visa-adjacent forms.
- **Test shape**: submit form A, submit form B with contradictory value; observe whether the SUT cross-checks. Most SUTs don't.
- **Business impact**: insurance fraud, identity-laundering, compliance failure.

### 4. Causal incoherence (effect before cause)

The actor performs an action whose timestamp precedes its supposed precondition.

- **CURA example**: book a follow-up appointment dated _before_ the initial consultation. Each is a legal future date when considered alone; the
  ordering violates causal sense.
- **Real-world inspiration**: a return-flight booking dated before the outbound. A wedding-anniversary entry dated before the marriage record.
- **Test shape**: create A; create B with a date < A's date and a "follow-up" relationship. Observe.
- **Business impact**: clinical-protocol violation, audit-trail nonsense, billing-cycle corruption.

### 5. Quantitative incoherence (sums / counts that can't be physically true)

The actor's actions, summed, exceed a real-world physical bound.

- **CURA example**: book appointments totalling 30 hours of clinical time in a single day. Each booking is a legal duration; the sum is impossible.
- **Real-world inspiration**: same person claiming gym attendance summing to >24 h in one day.
- **Test shape**: loop bookings, sum the durations, verify whether the SUT enforces any per-day cap.
- **Business impact**: resource exhaustion masquerading as legitimate scheduling.

### 6. Relational incoherence (relationships that contradict each other)

The actor creates two relationships that can't both be true.

- **CURA example**: register as the _patient_ on appointment A and as the _guardian_ on appointment B for a child whose declared birthdate makes A's
  patient impossible (the patient role would predate the guardian's adulthood).
- **Real-world inspiration**: same SSN as both employee and dependent on the same payroll record.
- **Test shape**: create relationships A and B; verify whether the SUT detects the contradiction.
- **Business impact**: fraud, benefits abuse, regulatory exposure.

## Procedure

### Step 1 — Anchor on the SUT's data model

Read enough of `CURA_FRD.md` to know what facts the SUT _stores about a user / booking / clinical record_. The incoherence dimensions only apply where
the SUT actually has data on both sides of the contradiction. If the SUT doesn't track location for bookings, §2 (spatial) doesn't produce encodable
tests — it produces a static observation ("SUT lacks the model").

For CURA specifically: the SUT tracks visit date, doctor, "facility" (in the FRD form), and the patient's identity via the demo account. It does _not_
track location coordinates, durations, or relationships. Adjust the catalogue accordingly.

### Step 2 — Walk the six dimensions against the SUT

For each dimension:

- Does the SUT have the fields needed to _express_ the incoherence? (If not → static observation, not encodable.)
- Is each step doable through the normal UI?
- Is the contradiction observable through the UI's response (rejection? warning? silent accept?)?
- Is the harm business-shaped?

If all yes: encodable candidate. If "SUT lacks the model" → static observation, still worth surfacing (the gap is the finding).

### Step 3 — Cross-check against existing artifacts

- Already in the suite? (Unlikely — this is a less-explored axis than saturation.) Silent if yes.
- Documented in `IDENTIFIED_GAPS.md`? Cross-reference.
- Adjacent to a `review-spec-gaps` finding? Note the linkage — incoherence questions often surface as "the spec doesn't define what happens if…".

### Step 4 — Cross-check against the hard line

For each candidate: does encoding require anything beyond the normal UI + legal inputs? If yes → out of scope. The whole skill collapses if a single
scenario crosses the line, so this check is per-scenario.

### Step 5 — Surface the catalogue

```markdown
# Incoherence-attack catalogue — `<SUT>` (<date>)

## Encodable scenarios (SUT has the data model + UI surface to expose the incoherence)

### Temporal incoherence

- **Scenario**: <one-sentence description with concrete values>.
- **Action shape**: <step A, step B, contradiction>.
- **SUT data required**: <fields the SUT must track for the contradiction to be visible>.
- **Detection question**: <"does the SUT reject step B?" / "does the SUT surface a warning?" / "is the contradiction recorded silently?">.
- **Business impact**: <who loses, how>.
- **Test shape (suggested)**: <create A → attempt B → observe response → assert against the FRD's stated behaviour, if any>.
- **Cross-reference**: `review-spec-gaps §<n>` (the spec may not even define expected behaviour) | `IDENTIFIED_GAPS.md §<ref>`.

### Spatial incoherence

- ...

### (...)

## Static observations (SUT lacks the data model — incoherence undetectable, gap worth noting)

- `<dimension>`: SUT doesn't track `<field>`, so `<incoherence example>` cannot be observed through the UI. Document as a model-level limitation, not
  a defect.

## Out-of-scope ideas considered and dropped

- `<idea>`: would require <protocol-level / injection-shaped / active-security> tooling. Dropped per the project's hard rule.

## Cross-references

- Sister skill: `business-attack-ideation` (volume / timing / identity attacks).
- Spec questions: `review-spec-gaps` is the natural follow-up for any scenario whose expected behaviour isn't in the FRD.
- `IDENTIFIED_GAPS.md` §<refs>.

## Recommended next motions

- For each encodable scenario: `empiricism` to verify the SUT's current behaviour, then `extend-coverage` to author the test.
- For each static observation: surface in a discussion artifact; consider whether the FRD should declare the model's limit.

## Verdict

<one-line: N encodable, K static-only, J out of scope, nothing material>.
```

Print the catalogue.

### Step 6 — Stop. The user decides.

Each encodable candidate can resolve as:

- **Encode** — `empiricism` to verify CURA's actual current behaviour, then `extend-coverage` to author the test (often as an intentional fail — the
  SUT likely doesn't detect the incoherence).
- **Discuss** — surface to stakeholders / spec authors before encoding. Incoherence detection is often a product decision, not a defect.
- **Defer** — record for the next coverage push.

Static observations don't get encoded. They feed `review-spec-gaps` ("the spec is silent on whether the SUT models X") or `update-frd-and-tests` (if
the team chooses to declare the model's bounds explicitly).

## Hard rules

- **Each individual step must pass the form's validation.** If a scenario requires a "non-legal" input, it's out of scope (and is just an injection
  attack in a clever costume).
- **The harm must be business-shaped.** "The database has a wrong row" is technical; "the patient gets a bill for a service they couldn't have
  received" is business-shaped.
- **The SUT data model gates encodability.** If the SUT doesn't track the dimension, you cannot encode the incoherence as a UI test — surface it as a
  static observation, not a test.
- **Don't blame the SUT for not modelling reality.** A SUT without a location model doesn't have a _bug_ in not detecting spatial incoherence — it has
  a _limitation_. The catalogue surfaces both, distinguished.
- **Don't sketch attack-shape payloads.** Per `CLAUDE.md`. Same line as the sister skill.
- **Cross-reference the spec.** Most incoherence scenarios collide with `review-spec-gaps` territory — they often surface "the spec doesn't say what
  happens" before they surface "the SUT does the wrong thing".
- **Verify SUT behaviour empirically before encoding.** A scenario whose test shape assumes "CURA accepts B silently" needs `empiricism` first.

## When to run this skill

- Coverage planning sessions — what reality-contradictions could the product silently accept?
- After a `business-attack-ideation` pass — the two skills cover adjacent territory; running both gives a fuller adversarial map.
- When the product team is reviewing fraud / abuse stories — the catalogue is a discussion artifact.
- After a spec change that adds new identity / relationship / location fields — does the new model close any previously-undetectable incoherence?

## What this skill does NOT do

- It does not encode tests. Use `extend-coverage` / `empiricism` after the user picks scenarios.
- It does not verify SUT behaviour. Use `empiricism` / `write-a-probe`.
- It does not propose injection, brute-force, or any active-security technique. Out of scope by rule.
- It does not produce attack payloads. Even illustrative ones.
- It does not run anything against the SUT. Static ideation only.
- It does not assess whether the SUT _should_ model a given dimension — that's a product decision, not a test decision.
