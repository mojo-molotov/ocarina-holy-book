---
name: persistence-attack-ideation
description:
  "**Black-hat skill for hardening existing access / permission / auth tests** by adding the dimension a polite user wouldn't add: *insistence*. The
  polite test types the wrong password once and observes the rejection. The hardened test types it five times, then ten, then a hundred — and checks
  whether the SUT degrades gracefully or starts behaving strangely. The polite test clicks a disabled button by waiting for it to enable; the hardened
  test forces a click via the UI (the button might *visually look* disabled but still respond to a focus + Enter keypress). The polite test navigates
  to a forbidden URL once and accepts the redirect; the hardened test navigates 50 times in 5 seconds, refreshes between each, opens the URL in three
  tabs, presses Back after each redirect. Every action is one a real user could perform through a normal browser — no curl, no fuzzer, no injection.
  The harm is that the SUT silently weakens: a button that visually-disables but functionally-doesn't, a rate-limit that exists in theory but doesn't
  trigger, an auth redirect that has a one-frame window where the protected page renders before the redirect. Generates hardening proposals for each
  existing access-style test (or as new tests adjacent to them). Use whenever the user asks to harden access tests, add insistence to permission
  tests, brainstorm 'what if the user just refuses to stop' scenarios, or audit whether rate-limits / disabled states / auth gates are *functionally*
  enforced or only *visually* enforced."
---

# Persistence-attack ideation — hardening through legitimate insistence

A black-hat ideation skill, third in the trio with `business-attack-ideation` (volume / aggregate harm) and `incoherence-attack-ideation` (impossible
combinations). This one is narrower:

> _Take an existing test that observes a permission, an access gate, a disabled state, or an auth redirect — and ask what happens when the user simply
> refuses to accept the SUT's answer the first time._

Polite tests confirm the gate works on a single attempt. Persistent tests confirm the gate works under **insistent legitimate retry**: rapid clicks on
a "disabled" button, repeated URL access via the address bar, multi-tab parallelism, back-button replay, refresh-spam. These are the actions a
real-but-determined user takes through a normal browser. They expose SUTs that _look_ secure but rely on the user being polite.

The skill's output is hardening proposals: for each existing access-style test, the additional insistence dimensions worth adding (or worth filing as
adjacent new tests).

## The hard line (same as siblings)

In scope:

- The user types a URL into the address bar. Legitimate.
- The user clicks a visible button — even one styled as disabled. Legitimate (the click is dispatched; whether it's _handled_ is the SUT's problem).
- The user presses Enter on a focused form. Legitimate.
- The user opens N tabs of the same URL. Legitimate.
- The user hits Refresh / Back / Forward repeatedly. Legitimate.
- The user submits the same form many times in succession. Legitimate.

Out of scope (per `CLAUDE.md` → _"Security testing is functional and static — never active"_):

- Forging an auth token in DevTools and pasting it into a cookie. Out — that's a protocol-level trick.
- Disabling JavaScript via DevTools to bypass a client-side gate. Out — that's an active-security technique even though DevTools is a normal browser
  feature; the _intent_ crosses the line.
- Editing the DOM via DevTools to enable a disabled button. Out — same reason.
- HTTP-level retry tooling (curl loops, brute-force frameworks). Out.
- Injection-shaped payloads anywhere. Out.

The line: **the user interacts through the rendered UI only**. The button is clicked by issuing a click event through the browser's normal dispatch on
the visible page. The URL is opened by typing into the address bar. No DevTools, no DOM editing, no protocol layer.

## The seven insistence dimensions

For each existing access / permission / auth test, walk these seven dimensions and ask: _does the test cover this insistence shape?_

### 1. Repeated identical attempt

The user attempts the same forbidden action N times in rapid succession.

- **Concrete example**: wrong-password login retried 20 times in 30 seconds. Polite test: 1 attempt, observe rejection. Hardened test: 20 attempts,
  observe whether the Nth one still shows the same rejection, whether any starts succeeding (rate-limit-then-bypass shape), whether the SUT eventually
  locks the account, whether the SUT degrades visibly (slow response, weird UI state).
- **Detection question**: does the SUT enforce a rate-limit? If yes, does it kick in _deterministically_ or only after the dyno wakes up? If no, what
  does the team want to do about it?

### 2. Forced UI interaction with a disabled element

The user issues UI events to elements that _appear_ disabled — disabled by CSS, by `aria-disabled`, by visual greying, by a missing onclick handler.

- **Concrete example**: the "Book Appointment" button might be disabled until all required fields are filled. Polite test waits for it to enable.
  Hardened test: focus the disabled button + press Enter, or click via JavaScript-free pure UI dispatch (Selenium's `.click()` is a real click event;
  whether the page handles it depends on the page's gating logic, not on the visual state).
- **Detection question**: is the disabled state _functional_ (the SUT rejects the submission) or only _visual_ (the click goes through, the form
  submits, the SUT processes a half-filled record)?
- **Note**: in the project's existing dispatcher work, the _random submit dispatchers_ (cross-ref `review-submit-dispatchers`) test different paths to
  confirm. The hardened variant is "what if I pick the path that _shouldn't_ work but the UI doesn't block me from trying?".

### 3. URL-typed direct access (bypassing UI gating)

The user types a URL directly into the address bar, never visiting the page that normally links to it.

- **Concrete example**: type `…/history.php` while logged out. Polite test does this once, observes redirect. Hardened test: type the URL, then press
  Back, then re-type, then refresh, then open in three tabs. Does the redirect hold under all those motions?
- **Detection question**: is there a one-frame window where the protected page renders before the redirect fires? (BFcache investigations like
  `§B-BROWSER-1` already touch this. The hardening lens extends it.)

### 4. Back / forward / refresh insistence

The user uses the browser's history navigation to revisit a state they shouldn't be able to revisit.

- **Concrete example**: logout, then press Back 5 times. Polite test: one Back. Hardened test: 5 Backs, 5 Forwards, 1 Refresh, repeat.
- **Detection question**: does the SUT's auth gate hold through every navigation primitive? (Cross-ref `§B-BROWSER-1` — the BFcache pair finding is
  exactly this shape on one back-press.)

### 5. Multi-tab parallelism

The user opens the same URL or starts the same flow in multiple tabs simultaneously.

- **Concrete example**: open the appointment form in three tabs, fill them with different (or identical) data, submit in rapid succession. Does the
  SUT treat them as three distinct bookings, dedup them, or behave inconsistently?
- **Detection question**: is the SUT's state model per-session or per-request? If per-session, do parallel tabs share state correctly?

### 6. Pre-emptive submission (form filled, gate not yet open)

The user fills a form before the gating condition is met (e.g. session still loading, user just-logged-out but the form is still rendered), and
submits.

- **Concrete example**: open the appointment form, immediately click logout _in another tab_, then submit the form in the original tab. The session is
  dead but the form was filled while it lived.
- **Detection question**: is the submission validated against the _current_ session state, or against the state at form-load?

### 7. Persistent state replay

The user replays a previously-valid action after the conditions for it have changed.

- **Concrete example**: book an appointment, then duplicate the tab (or copy the URL), then re-submit. Or: log in, copy a URL, log out, navigate to
  the copied URL in a new session.
- **Detection question**: does the SUT carry any state in URLs / query params that survives session change?

## Procedure

### Step 1 — Inventory existing access / permission / auth tests

```bash
grep -rn "login\|auth\|logout\|permission\|access\|history\|redirect" src/tests/scenarios
```

For each test found, capture: name, what gate it verifies, which of the seven insistence dimensions (if any) it already exercises.

### Step 2 — Walk the seven dimensions per test

For each (test × dimension) pair, ask:

- Is this dimension already covered? (Some are — the project's BFcache work covers §4 partially.)
- Is the dimension _encodable_ through the normal UI (no DevTools tricks)?
- Is the harm meaningful — does it matter to the business?
- Does the FRD even define expected behaviour? (Often it doesn't — `review-spec-gaps` territory.)

### Step 3 — Cross-check against the hard line

Per dimension and per proposal: does encoding it require anything beyond normal UI interaction? If yes — drop. The hardening lens is about
_insistence_, not about reaching past the UI.

### Step 4 — Cross-check against existing artifacts

- Already encoded? Silent.
- Already in the gap inventory? Cross-reference.
- Adjacent to a `review-spec-gaps` finding? Note the linkage — the FRD often won't define what the hardened behaviour _should_ be, so this is also a
  spec-gap pass.
- Adjacent to a `business-attack-ideation` or `incoherence-attack-ideation` finding? Note overlap.

### Step 5 — Surface the hardening proposals

```markdown
# Persistence-attack hardening — `<SUT>` (<date>)

## Existing tests audited

- `<test name>` — gate `<…>`, dimensions currently exercised: `<list>`.

## Hardening proposals

### `<existing test or new test name>` — dimension §<n>

- **Polite behaviour today**: <one sentence>.
- **Insistence to add**: <concrete action sequence — all UI>.
- **Detection question**: <what new behaviour the hardened test would observe>.
- **Expected SUT response per the FRD**: <quoted | "spec silent — also a spec-gap finding">.
- **Business impact if SUT degrades under insistence**: <one sentence>.
- **Test shape (suggested)**: <encode as new test | extend existing test with parametrisation>.
- **Cross-reference**: `review-spec-gaps §<n>` | `the gap inventory <entry-ref>` | `review-submit-dispatchers` | etc.

## Out-of-scope ideas considered and dropped

- `<idea>`: requires <DevTools manipulation / protocol-level trick / DOM editing>. Dropped per the hard line.

## Cross-references

- Sister skills: `business-attack-ideation`, `incoherence-attack-ideation`.
- Spec-gap follow-ups: most proposals collide with `review-spec-gaps` — the FRD often doesn't define the hardened behaviour.
- Empirical follow-up: `empiricism` to verify the SUT's actual behaviour before encoding any hardened assertion.

## Recommended next motions

- For each proposal: `empiricism` to observe the SUT's current behaviour, then `extend-coverage` to author the hardened test.
- For each spec-gap surfaced by the proposal: bundle into the next `review-spec-gaps` pass.

## Verdict

<one-line: N hardening proposals, K already covered, J spec gaps surfaced, nothing material>.
```

Print the catalogue.

### Step 6 — Stop. The user decides.

Each proposal resolves as:

- **Encode** — `empiricism` to verify, then `extend-coverage` to author.
- **Defer** — record for the next coverage push.
- **Discuss** — many hardening behaviours are product decisions (does the team _want_ the SUT to lock the account after 20 wrong-password attempts?).

## Hard rules

- **UI-only.** No DevTools editing, no DOM manipulation, no JavaScript console use. Address bar, buttons, forms, browser history controls — that's the
  surface.
- **Insistence is the lens.** Each dimension is "what if the user does this _more_ than the polite test does?". If the proposal is "what if the user
  does something _different_", it's `business-attack-ideation` or `incoherence-attack-ideation` territory.
- **A button click is legitimate even when the button looks disabled.** The browser dispatches the click; whether the page handles it is the SUT's
  responsibility. The hardened test confirms the SUT's enforcement, not the CSS.
- **No rate-limit _bypass_ attempts.** The hardened test confirms the rate-limit _exists_ (or surfaces that it doesn't). It does not try to evade an
  existing rate-limit through clever timing — that crosses the line.
- **Spec gaps are expected.** The FRD usually doesn't define hardened behaviour. Cross-referencing `review-spec-gaps` is part of the motion.
- **Verify before asserting.** A hardened test that _asserts_ "the 21st login attempt is locked out" needs `empiricism` to observe the SUT's current
  behaviour before encoding the assertion.

## When to run this skill

- Coverage planning for access / auth / permission tests — what insistence dimensions are missing?
- After a `business-attack-ideation` or `incoherence-attack-ideation` pass — completes the black-hat trio.
- Before a security review (the _functional_ part) — hardened tests demonstrate that gates hold under insistence, not just on the polite first try.
- After the SUT adds (or changes) any access gate — does the new gate hold under the seven dimensions?
- During stakeholder review of product robustness — the catalogue is a discussion artifact.

## What this skill does NOT do

- It does not encode the tests. Use `empiricism` + `extend-coverage` after the user picks proposals.
- It does not propose DevTools manipulation, DOM editing, console-based bypass, or any technique beyond normal UI interaction.
- It does not produce injection payloads, brute-force tooling, or active-security techniques. Hard rule.
- It does not file the gap inventory entries directly. Cross-references are recommended; entries are a follow-up via `update-frd-and-tests`.
- It does not run anything against the SUT. Static ideation only.
- It does not assess whether the SUT _should_ enforce a given gate harder — that's a product decision, not a test decision.
