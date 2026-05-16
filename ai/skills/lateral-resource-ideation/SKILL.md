---
name: lateral-resource-ideation
description:
  "**Black-hat skill in the spirit of IDOR (Insecure Direct Object Reference), restricted to URL-only manipulation through the normal address bar.**
  No request interception, no header forgery, no curl, no proxy. The user has legitimate access to resource `/appointment/123`; they type
  `/appointment/124` into the address bar; what happens? The SUT might redirect cleanly, return 403, return 404, or quietly render someone else's
  appointment. The audit walks every URL-addressable resource in the SUT and asks, per resource, *'is access enforced when the user just guesses a
  neighbouring identifier?'*. Covers sequential IDs, predictable patterns (date-based, padded sequences), lateral resource-type swaps
  (`/appointment/123` → `/history/123`), query-parameter manipulation (`?user_id=mine` → `?user_id=other`), pagination beyond owned range, and filter
  parameter flips — all observable through the address bar alone, no protocol-level tools. Generates a catalogue of lateral-access scenarios with the
  test shape (functional, UI-only) that observes whether the SUT enforces access at the resource level or only at the navigation level. Use whenever
  the user asks to audit lateral access, find IDOR-shaped exposures, brainstorm URL-guessing scenarios, or harden resource-access tests beyond the
  happy-path."
---

# Lateral-resource ideation — neighbouring IDs through the address bar

A black-hat ideation skill, sixth in the series with `business-attack-ideation`, `incoherence-attack-ideation`, `persistence-attack-ideation`,
`permission-appropriateness-audit`, and `bfcache-exposure-ideation`. The lens here is sharp and narrow:

> _The user has access to one resource. The URL that identifies it differs by a small, guessable change from the URL of a resource they shouldn't have
> access to. Does the SUT enforce access when the user makes that change in the address bar?_

This is the spirit of IDOR (Insecure Direct Object Reference), restricted by the project's hard rule to **URL-only manipulation through the normal
address bar**. No request interception, no custom headers, no curl, no proxy. The user types a URL; the browser displays what the SUT chooses to
return; the audit observes.

Per `CLAUDE.md` → _"Security testing is functional and static — never active"_. Typing a URL is a normal browser action; intercepting and rewriting an
HTTP request is not. The whole skill rests on that distinction.

## The hard line

In scope:

- Type a URL with a different ID into the address bar. Legitimate.
- Bookmark a URL while authenticated, open it later. Legitimate.
- Copy a URL someone else shared (or one the SUT exposed in an email / share button) and open it. Legitimate.
- Modify a query string in the address bar (`?id=1` → `?id=2`). Legitimate.
- Modify a fragment (`#section=mine` → `#section=other`). Legitimate.
- Drop a query parameter (`?private=true` removed). Legitimate.

Out of scope:

- Intercepting an HTTP request with a proxy. Out.
- Adding / modifying headers (Authorization, Cookie, Referer). Out — that requires DevTools / proxy / curl.
- Crafting POST bodies. Out — same.
- Using DevTools' Network panel to _replay_ a request with different parameters. Out — that's request crafting at the protocol level.
- Brute-forcing IDs at HTTP rate. Out.

The line: **the URL is typed (or pasted) into the address bar; the request is whatever the browser produces from that URL alone, with whatever
cookies/session the browser already has**. No additions, no rewrites.

## What "different identifier" means here

The audit hunts for URL-shaped resource references the user _might_ be able to guess. Useful patterns:

- **Sequential integer**: `…/appointment/123` → `…/appointment/124`.
- **Date-based**: `…/visits/2026-05-15` → `…/visits/2026-05-14` (often used for daily reports).
- **Padded sequential**: `…/invoice/00045` → `…/invoice/00046` (leading-zero formats).
- **Slug-based with predictable shape**: `…/profile/jdoe` → `…/profile/janedoe`.
- **Date + ID combination**: `…/report/2026-05-15-001` → `…/report/2026-05-15-002`.
- **URL-embedded "scope"**: `…/team/mine/orders` → `…/team/all/orders`.

When the SUT uses opaque random IDs (UUIDs, signed tokens), most of these patterns don't apply — the audit still surfaces _whether opaqueness is the
only barrier_, which is a useful question for the team to acknowledge.

## The seven lateral-access dimensions

For each, walk the SUT's URL surface and ask whether the dimension yields encodable scenarios.

### 1. Sequential ID enumeration

The user changes a numeric ID by ±1 (or by larger steps) in the address bar.

- **CURA example**: CURA's session-based model doesn't expose resource IDs in URLs prominently (verify per `empiricism`). For SUTs that do: walk every
  numeric-ID URL and pair each with a ±1, ±10, ±1000 lateral move.
- **Detection question**: does the SUT respond with content, with a generic 403/404, or with a tailored "you don't have access to this record"?
- **Note**: a tailored response can be itself a side channel (existence-vs-permission disclosure); the audit surfaces _both_ the access question and
  the response-shape question.

### 2. Predictable-pattern guessing

The IDs follow a pattern (date, sequence with padding, predictable slug). The user guesses neighbouring values.

- **Test shape**: enumerate URLs along the pattern, observe responses.
- **Detection question**: same as §1 — and additionally, _does the pattern itself leak information_ (e.g. a tomorrow's-date URL revealing draft
  state)?

### 3. Resource-type lateral swap

The user keeps the same ID but changes the resource type in the path.

- **CURA example**: `…/appointment/<id>` → `…/history/<id>` → `…/profile/<id>`. Do the URLs even share an ID space? If yes, swapping the segment may
  expose neighbouring data.
- **Detection question**: does the SUT validate that the ID belongs to the resource type, or just looks it up?

### 4. Query-parameter scope expansion

The user modifies a query parameter to broaden the access scope.

- **Examples**: `?scope=mine` → `?scope=all`; `?user_id=42` → `?user_id=43`; `?team=marketing` → `?team=finance`.
- **Detection question**: does the server validate the scope against the session's permissions, or trust the parameter?

### 5. Query-parameter constraint removal

The user removes a query parameter that was acting as a filter.

- **Examples**: drop `?status=published` (was filtering to public posts; without it, drafts may show); drop `?owner=me` (was filtering to own
  records).
- **Detection question**: does the SUT enforce defaults when constraints are absent, or interpret absence as "no constraint"?

### 6. Pagination beyond owned range

The user manipulates pagination parameters to walk past their own data.

- **Examples**: `?page=1` (owned) → `?page=999`; `?offset=0&limit=10` → `?offset=10000&limit=100000`.
- **Detection question**: does pagination return only the caller's records on every page, or does an out-of-range page return _some_ records from
  another tenant / user?

### 7. Fragment / anchor manipulation

URLs with state encoded in the fragment (`#…`). The user changes the fragment.

- **Examples**: `#section=public` → `#section=private`; `#tab=overview` → `#tab=admin`.
- **Detection question**: is the fragment a UI hint (purely client-side) or does the SUT condition on it for content visibility? Often the former,
  occasionally the latter — and the latter is the risky case.

## Procedure

### Step 1 — Inventory URL-addressable resources

```bash
grep -rn -i "_URL\|url\|path\|route\|endpoint" src/constants
grep -rn "REQ-" CURA_FRD.md | grep -i "url\|page\|resource"
```

Build the list of URLs the SUT exposes — including those embedded in code as constants, mentioned in the FRD's form table, or visible in routing
configs. For each URL, note: does it contain an ID? What kind (numeric, slug, UUID, date)? Are there query parameters or fragments?

For CURA specifically: the URL surface is short — `LOGIN_URL`, `HOME_URL`, `HISTORY_URL`, the appointment form URL, the profile URL. Most have **no
exposed IDs** (session-scoped). The audit's output will be brief; the first finding is therefore _"CURA exposes few resource IDs in URLs — the attack
surface is narrow by construction"_. The lens stays ready for future URL additions.

### Step 2 — Walk the seven dimensions × URLs

For each URL × dimension:

- Is the dimension applicable? (No ID → §1, §2 don't apply.)
- What's the _neighbouring_ resource the user shouldn't see? Pin a concrete example.
- Does the SUT have multi-user data that _could_ be exposed laterally? (CURA's single demo account makes this delicate — the "other user's data" is
  the same account; cross-tab tests may still apply.)
- Is encoding the scenario through the address bar alone?

### Step 3 — Cross-check against existing artifacts

- Already documented in `IDENTIFIED_GAPS.md`? Cross-reference.
- Adjacent `review-spec-gaps` finding? Cross-reference — most lateral-access questions also surface as "the spec doesn't say what happens".
- Adjacent `permission-appropriateness-audit §6` (implicit roles) or `§7` (resource-grouping)? Cross-reference.

### Step 4 — Cross-check against the hard line

Per proposal: does the test shape require headers, intercepted requests, or anything beyond typing in the address bar? If yes — drop.

### Step 5 — Surface the catalogue

```markdown
# Lateral-resource catalogue — `<SUT>` (<date>)

## URL surface

- `<url constant or path>` — IDs: `<numeric | slug | UUID | date | none>`. Query: `<list params | none>`. Fragment: `<used | not used>`.
- ...

## Encodable scenarios

### Sequential ID enumeration

- **`<url>` ID ±N**: <concrete example>. Detection question: <one sentence>. Test shape: drive `<owned URL>` → type `<lateral URL>` in address bar →
  observe response. Cross-reference: `IDENTIFIED_GAPS.md §<ref>` | new.

### Predictable-pattern guessing

- ...

### Resource-type lateral swap

- ...

### Query-parameter scope expansion

- ...

### Query-parameter constraint removal

- ...

### Pagination beyond owned range

- ...

### Fragment / anchor manipulation

- ...

## Static observations (no encodable test — recorded for awareness)

- `<URL>` uses opaque IDs (UUIDs). Direct enumeration impractical. The protection is non-trivial, but the audit notes that opaqueness is the only
  barrier — _should the SUT also enforce access at the row level?_ Question for the team.

## Out-of-scope ideas considered and dropped

- `<idea>`: would require <intercepted request / custom header / proxy>. Dropped per the hard line.

## Cross-references

- Sister skills: `business-attack-ideation`, `incoherence-attack-ideation`, `persistence-attack-ideation`, `permission-appropriateness-audit`,
  `bfcache-exposure-ideation`.
- Spec-gap follow-ups: `review-spec-gaps` for proposals where the FRD doesn't define expected behaviour.
- Empirical follow-up: `empiricism` to verify the SUT's current behaviour before encoding.

## Recommended next motions

- For each encodable scenario: `empiricism` to observe, `extend-coverage` to author.
- For static observations: discussion with the team; note in the FRD if the team wants to declare the protection model.

## Verdict

<one-line: N encodable, K static-only, J already-covered, nothing material>.
```

Print the catalogue.

### Step 6 — Stop. The user decides.

Each encodable candidate resolves as:

- **Encode** — `empiricism` to verify, then `extend-coverage` to author. Expect: tests often present as _intentional fails_ until the SUT enforces
  row-level access, mirroring the project's §9 gap-test discipline.
- **Discuss** — many lateral-access boundaries are product decisions (sharing a public URL is fine; sharing a record URL with a non-recipient is not —
  team draws the line).
- **Defer** — record for the next coverage push.

Static observations don't get encoded; they feed `review-spec-gaps` or `update-frd-and-tests`.

## Hard rules

- **Address bar only.** Typing, pasting, bookmark-opening, share-link-opening. Nothing past that.
- **No header / cookie manipulation.** The browser sends whatever it already has. The test does not modify cookies, add Authorization headers, or
  intercept anything.
- **No DevTools-based replay.** Re-issuing a request from the Network panel with parameters changed is _protocol-level_; out of scope.
- **Opaque IDs are not a free pass.** A SUT that uses UUIDs is harder to enumerate, but the audit surfaces _whether opaqueness is the only barrier_ as
  a question for the team.
- **A "tailored" 403 response is itself a side channel.** Surface that observation when applicable — the audit asks both the access question and the
  response-shape question.
- **Per `CLAUDE.md`: security testing is functional and static — never active.** This skill respects the line by construction.
- **Cross-reference `review-spec-gaps`.** Most lateral-access questions also surface "the FRD doesn't define expected response when the ID isn't in
  the caller's scope".
- **Verify SUT behaviour empirically before encoding.** A scenario asserting "the SUT redirects on `/appointment/<other-id>`" needs `empiricism`
  first.

## When to run this skill

- Coverage planning for resource-access tests.
- A new resource type exposes IDs in URLs.
- A new query parameter is introduced and the team wants to vet its constraint behaviour.
- After a `permission-appropriateness-audit` surfaces ambiguous role-vs-resource access — this skill is the natural follow-up at the URL level.
- Onboarding a contributor — the catalogue maps the URL surface and the implicit protection assumptions.

## What this skill does NOT do

- It does not encode tests. Use `empiricism` + `extend-coverage` after the team picks proposals.
- It does not intercept, craft, or modify HTTP requests. No proxies, no curl, no DevTools replay.
- It does not run anything against the SUT. Static ideation only.
- It does not produce attack payloads, ID dictionaries, or enumeration tooling.
- It does not file `IDENTIFIED_GAPS.md` entries directly. Cross-references are recommended; entries are a follow-up via `update-frd-and-tests`.
- It does not pick the team's protection model — the team decides where to enforce row-level access, where to rely on opaqueness, where to accept
  exposure.
