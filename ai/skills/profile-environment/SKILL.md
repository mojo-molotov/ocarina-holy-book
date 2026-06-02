---
name: profile-environment
description:
  "**Profile the engagement envelope — how much latitude the human grants the LLM on this SUT — and emit it as governance rules the rest of the
  battery obeys.** The Holy Book's `CLAUDE.md`, the skills, and the worked examples are all written at *maximum latitude* (CURA is an open-source
  public demo: read the SUT's source via `gh api`, probe the live app, public credentials, open-web research). A real engagement is narrower. This
  skill runs the *profiling interview* — like profiling a client before a commercial operation — across seven latitude dimensions (source access,
  live-system probing, data sensitivity, egress & confidentiality, the security-testing ceiling, autonomy & approval cadence, the repo/CI/PR change
  surface), resolves each *with the human* (stakeholder decisions, not code-derivable facts), and writes a tracked **`CLAUDE.profile.md`** appendix
  that `setup-environment` concatenates into the suite's `CLAUDE.md`. It is a **ratchet toward restriction** — it only ever *tightens* the defaults
  and the security hard line, never loosens them. TRIGGER when starting or onboarding an engagement that isn't the open public-demo case (a client
  site, an internal app, an NDA, a regulated/live-PII SUT); when the user says the assistant 'can't read the source / can't probe prod / staging-only
  / can't go on the web / it's under NDA / that's real customer data / needs sign-off before runs / is surface-only' on a SUT; or when asked to set
  the ground rules, boundaries, latitude, or 'what the AI is allowed to do' before testing — and re-run when the terms change (demo→client,
  staging→prod, an NDA lands, the repo goes private). SKIP — these belong to neighbours, not here: standing up the venv / tooling / driver adapter
  (`setup-environment`); mapping SUT parallel-safety bounds like session caps or rate limits (`understand-sut-constraints`); actually researching the
  SUT on the web (`assess-ecosystem`); writing a probe (`write-a-probe`) or verifying SUT behaviour (`empiricism`); recording driver paths in
  `CLAUDE.local.md`; configuring Claude Code permissions / allowlists so the harness stops prompting on commands (that's harness settings, not the
  engagement envelope); moving credentials into `constants` (code hygiene); or one-off chores like redacting a single screenshot. This skill sets the
  *policy*; those skills do the *work* inside it."
---

# Profile the environment — set the engagement envelope before the battery runs at full latitude

A governance skill. `setup-environment` wires the mechanics (venv, tooling, adapter, paths) and `understand-sut-constraints` maps the SUT's
parallel-safety bounds. Neither asks the question this skill exists for: **how much latitude does the human actually grant the LLM on this SUT?**

The whole battery has a silent default answer, and it is **"maximum"**. The Holy Book was authored against CURA — an open-source, throwaway, public
healthcare demo with hardcoded public credentials. So the rules read: _read the SUT's source before theorising_ (`gh api` the PHP), _drive a throwaway
probe against the live app when the error surface is thin_, _research the ecosystem on the open web_ (`assess-ecosystem`), _credentials live in
`src/constants/` because they're public_. Every one of those is a latitude the engagement happened to grant. On a real client site, most of them are
narrower or gone.

This skill profiles the engagement — the way a consultant profiles a client before an operation — and turns the answers into rules the rest of the
battery obeys. The deliverable is a tracked **`CLAUDE.profile.md`** appendix that `setup-environment` concatenates into the suite's `CLAUDE.md`.

## The one invariant: the profile only tightens, never loosens

The maximum-latitude default is also the **ceiling**. The profile is a **ratchet toward restriction** — every dimension below can be set _more_
restrictive than the Holy Book default, never less. Two consequences worth stating plainly, because they're the failure mode this skill must not
enable:

- **The `CLAUDE.md` security hard line is invariant.** _"Security testing is functional and static — never active"_ is an architectural property of
  the suite, not a latitude knob. A client saying _"it's our app, you may run sqlmap against it"_ does **not** unlock active testing here — that is a
  different kind of engagement (Burp / ZAP / a pentest contract) with its own tooling and rules, out of scope for an Ocarina functional suite. The
  profile can forbid even the _static_ source-reading the hard line permits; it can never grant the active testing the hard line forbids.
- **No dimension is loosened "because the client allowed it".** The profile's job is to record what the engagement _withdraws_ from the open default,
  not to expand the default. If the engagement genuinely is the open public-demo case, the profile says so (every dimension at "open") and changes
  nothing — that's a valid, complete output.

If you ever find yourself writing a profile rule that lets the LLM do _more_ than the Holy Book default, stop: that's not this skill.

## The seven latitude dimensions

For each: _what the open default assumes, what narrower settings look like, and the concrete rules a narrower setting imposes on the rest of the
battery._ The CURA worked example is the **"open" anchor** for every dimension — it's what "maximum latitude" actually looked like.

### 1. Source access — may the LLM read the SUT's source?

- **Open** (CURA): the SUT is open source; `gh api repos/<org>/<repo>/contents/<file> --jq '.content' | base64 -d` is the worked-example command. The
  `CLAUDE.md` rules _"Verify SUT behaviour — don't theorise"_ and _"Inspect the SUT for security / spec gaps"_ lean on this hard.
- **Source-available** — readable under licence/NDA terms, but reads may be logged, time-boxed, or limited to named files. Reading is allowed; bulk
  cloning or pulling the whole tree may not be.
- **Closed** — browser + FRD only. The LLM never sees server code. The two source-reading rules above are **suspended**: every server-side claim must
  be verified through the browser (rendered HTML, visible errors, URL changes) or against a contract artifact (OpenAPI / GraphQL schema) if one is
  provided — never by reading source, because there's no source to read.

**Why it matters:** half the `CLAUDE.md` hard-won rules ("read the PHP", "cite the file/function inline", "grep the rest for the same pattern") assume
source access. On a closed SUT those rules don't just not-apply — following them is impossible, and a profile that doesn't say so leaves the LLM
inventing source citations it can't have.

### 2. Live-system probing — may a throwaway probe hit the running SUT, and which deployment?

- **Open** (CURA): `write-a-probe` drives the live demo freely — that's the point of a probe, to remove inference by observing runtime state.
- **Staging-only** — probes may hit a staging/UAT deployment but **never production**. The reason is usually that prod carries real data or real
  users, or that prod traffic is monitored and a probe looks like an incident.
- **No live probing** — `write-a-probe` is suspended against this SUT. The LLM verifies from artifacts (recorded HAR, provided fixtures, the FRD, a
  contract schema) instead. `empiricism`'s "verify before encoding" still holds — but the verification instrument can't be a live probe.

**Why it matters:** a probe is the battery's empirical instrument. When it's off, the LLM must _say_ "this rests on the FRD's claim, unverified
against the live system" rather than silently proceeding as if it had probed — the difference between an honest gap and a fabricated certainty.

### 3. Data sensitivity — what is the test data, and what may touch the report?

- **Open** (CURA): hardcoded public demo credentials (`John Doe` / `ThisIsNotAPassword`) live in `src/constants/`; screenshots in the DOCX proofs show
  whatever the demo renders, because none of it is real.
- **Synthetic** — purpose-made test accounts, no real PII, but credentials are still secrets (project secret-handling convention; never in source).
- **Real / regulated** — the SUT holds real PII, PHI, financial, or otherwise regulated data. This reaches deep into the suite: **screenshots and DOCX
  proofs embed the rendered page**, so a proof of a page showing real data _is_ a data leak that lands in `.reports/` and possibly a PR. The profile
  must impose redaction/masking, restrict where reports may go, and forbid real values in test names, log messages, and datasets (which `CLAUDE.md`
  already routes through `src/constants/` — but now those constants are secrets, not public literals).

**Why it matters:** the report pipeline is built to be _shared_ (DOCX proofs, JSON results, PR artifacts). Under real data that sharing becomes
exfiltration. This is the dimension most likely to cause real harm, so it's the one to ask about most carefully.

### 4. Egress & confidentiality — may information leave the environment?

- **Open** (CURA): `assess-ecosystem` researches the SUT on the open web; findings can go in a public GitHub PR; the SUT name and URLs are public.
- **Limited** — web research allowed in general but the SUT's name/URLs/internal details must not be sent to external services (so
  `assess-ecosystem`'s queries are scrubbed, or it's run only against the SUT's _own_ public docs).
- **Air-gapped / NDA** — no egress. `assess-ecosystem` and any `WebFetch` / `WebSearch` of SUT-related material are suspended; nothing about the SUT
  goes to a public repo; even the conversation is confidential. PRs and findings stay in the private repo.

**Why it matters:** several skills reach outward by default (web research, public PR descriptions). Under an NDA those defaults breach the engagement.
The profile names what may cross the boundary so the LLM doesn't have to guess mid-task.

### 5. Security-testing ceiling — the invariant floor, restated per engagement

`CLAUDE.md`'s _"Security testing is functional and static — never active"_ is the ceiling for **every** engagement and **cannot be raised** (see the
invariant above). What the profile records here is whether the engagement _lowers_ it further:

- **Default** (CURA): functional + static gap analysis is welcome — read the source for gaps, write functional tests that exercise security-relevant
  behaviour through the normal UI.
- **Static suspended** — closed source (dimension 1) removes the static half by force; only functional-through-the-UI security behaviour remains.
- **Security testing out of scope entirely** — the engagement wants functional coverage only, no security-relevant tests at all, even the
  through-the-UI ones (no "submit empty date to check server-side validation", no "assert no CSRF input"). Some clients scope security to a separate
  vendor and want the functional suite to stay clear of it.

**Why it matters:** this dimension only ever subtracts. Writing it down stops the LLM from treating CURA's rich gap-analysis worked examples as a
licence to go hunting for gaps on an engagement that didn't ask for them.

### 6. Autonomy & approval cadence — what may the LLM do before a human signs off?

- **Open** (CURA): the battery's standard cadence — surface analyses for sign-off (every `review-*` / `assess-*` skill), but author tests and run them
  freely, with the one hard gate that `CLAUDE.md` already sets: **dataset changes stop and ask** ("Datasets are authoring decisions").
- **Sign-off before runs** — the LLM may author, but running anything against the live SUT needs a human present / explicit go-ahead (common when runs
  cost money, touch shared state, or are monitored).
- **Surface-only** — the LLM proposes; a human applies every edit. No autonomous writes to the suite at all.

**Why it matters:** this is the literal human↔LLM interaction contract the engagement wants. The default cadence is tuned for a throwaway demo where a
bad run costs nothing; raise the stakes and the human wants more gates. Stating the cadence once, up front, beats re-negotiating it on every action.

### 7. Change surface — what may the LLM touch in the repo and its pipeline?

- **Open** (CURA): author tests/POMs/scenarios, push branches, open PRs to a public repo. `setup-environment` already fences the genuinely off-limits
  surfaces (it doesn't edit CI workflows; it never touches the SUT).
- **Restricted repo** — no pushing to certain branches, no PRs to the client's repo (work lands on a fork or a delivery branch), CI is owned by the
  client and never edited.
- **Sandbox only** — work stays in a local working copy; nothing is pushed anywhere until a human moves it.

**Why it matters:** the open default assumes the LLM owns the repo it's working in. On a client engagement it usually doesn't, and "open a PR" — a
no-op courtesy on a public demo — can be a boundary violation.

## Reference profiles — shorthand, not boxes

The seven dimensions are set **independently** (a SUT can be open-source _and_ hold real PII — dimension 1 "open", dimension 3 "real"). But three
recurring combinations are worth a name as a starting vocabulary:

| Profile          | 1 Source  | 2 Probing | 3 Data    | 4 Egress   | 5 Security            | 6 Autonomy        | 7 Change surface |
| ---------------- | --------- | --------- | --------- | ---------- | --------------------- | ----------------- | ---------------- |
| **Open** (CURA)  | open      | live      | public    | open       | functional+static     | author + run      | own repo / PRs   |
| **Internal**     | available | staging   | synthetic | limited    | functional+static     | run with sign-off | delivery branch  |
| **Confidential** | closed    | none      | real      | air-gapped | functional only / OOS | surface-only      | sandbox          |

Pick the closest as a starting point, then adjust each dimension to what the engagement actually grants. The table is a conversation-starter; the
per-dimension settings are the real output. Never report only the tier label — the dimensions are what the rules are generated from.

## Procedure

### Step 1 — State the baseline, then run the profiling interview

Open with the invariant: the battery defaults to **Open**, and the profile can only narrow it. Then walk the seven dimensions **with the human** —
these are stakeholder decisions (contractual, legal, data-governance), not facts you can grep out of the repo. Frame it as profiling the engagement:

> "I'm going to set the latitude this suite operates under. The Holy Book assumes an open public demo — read the source, probe the live app, research
> on the web, public credentials. For each of these seven, tell me what _this_ engagement allows. Anything you don't restrict stays at the open
> default."

Ask per dimension; capture the setting **and the one-line reason** (the reason is what makes the rule defensible later — same discipline as
`understand-sut-constraints`' "is it specified?"). Where the codebase already hints at the answer (an NDA notice in the README, a private repo, a
`*.internal` SUT URL, secrets handled via a vault rather than `src/constants/`), surface the hint and **confirm** — don't infer the whole envelope
from one signal.

### Step 2 — Resolve each dimension to its rule deltas

For each dimension set below "open", write down _which `CLAUDE.md` sections and which skills the setting changes_, concretely:

- Source closed → suspends _"Verify SUT behaviour — read the source"_ and _"Inspect the SUT for gaps"_; verification falls back to browser + contract.
- Live probing off → suspends `write-a-probe` against the SUT; `empiricism` verifies from artifacts and **labels unverified claims as unverified**.
- Real data → redaction on screenshots/DOCX, reports stay in `<named location>`, no real values in names/logs/datasets.
- Air-gapped → suspends `assess-ecosystem` / `WebFetch` / `WebSearch` on SUT material; PRs and findings stay private.
- Security narrowed → which test categories are now out of scope.
- Autonomy narrowed → which actions now need sign-off (author / run / any write).
- Change surface narrowed → where work may land; what's never pushed/edited.

### Step 3 — Check the invariant

Before emitting: re-read the resolved set and confirm **nothing loosens** the open default or the security hard line. If a requested setting would
grant _more_ latitude (active security testing, reading source the licence forbids being reframed as "allowed"), stop and tell the user that's outside
what this skill — or this suite's philosophy — can grant. The ratchet only turns one way.

### Step 4 — Emit `CLAUDE.profile.md`

Write the appendix to the suite root (a **tracked** file — the engagement envelope is shared by the whole team, unlike per-machine `CLAUDE.local.md`).
It is a **generated artifact**, regenerated when the engagement changes, exactly like the adapter appendix. Shape:

```markdown
# Engagement profile — `<SUT / client>` (<date>)

> Generated by `profile-environment`. This appendix **tightens** the `CLAUDE.md` core for this engagement. It never loosens the core or the security
> hard line. Regenerate when the engagement's terms change.

## Profile: <Open | Internal | Confidential | custom>

| Dimension        | Setting                                        | Reason (one line) |
| ---------------- | ---------------------------------------------- | ----------------- |
| Source access    | <open/avail/closed>                            | <why>             |
| Live probing     | <live/staging/none>                            | <why>             |
| Data sensitivity | <public/synthetic/real>                        | <why>             |
| Egress           | <open/limited/air-gapped>                      | <why>             |
| Security ceiling | <functional+static / functional / OOS>         | <why>             |
| Autonomy         | <author+run / run-with-signoff / surface-only> | <why>             |
| Change surface   | <own repo / delivery branch / sandbox>         | <why>             |

## Rules in force this engagement

<For every dimension set below "open", the concrete rule and the CLAUDE.md section / skill it overrides. Phrase as imperative rules the next reader
obeys, e.g.:>

- **No source reading.** The SUT is closed; `CLAUDE.md` → "Verify SUT behaviour" / "Inspect the SUT for gaps" are suspended. Verify every server-side
  claim through the browser or the provided OpenAPI contract; never cite a source file (there is none to cite).
- **No live probing.** `write-a-probe` is off against this SUT. `empiricism` verifies from `<artifacts>`; label any claim that can't be verified as
  "unverified — FRD only".
- **Real data — reports are sensitive.** Screenshots and DOCX proofs may show live PII; redact per `<convention>`; `.reports/` stays in `<location>`
  and is never attached to a public PR.
- <… one bullet per narrowed dimension …>

## Unchanged (still at open default)

- <dimensions left open — state them, so a reader knows they're deliberate, not forgotten>.
```

### Step 5 — Hand off to `setup-environment` for assembly

`profile-environment` writes the appendix; `setup-environment` Step 7 concatenates it into the suite's `CLAUDE.md` (core + adapter appendix +
**profile appendix**). If `setup-environment` has already run, re-run its Step 7 alone to fold the new profile in. If the profile changes later,
regenerate here (Steps 1–4) then re-run Step 7 — same copy-not-symlink lifecycle as the adapter appendix and the skill-battery copy.

### Step 6 — Surface the summary; the human signs off

Print the profile table and the rules-in-force list. The human confirms the envelope before any further work runs under it. The envelope is the
deliverable; everything downstream (which tests get written, which probes get run) now operates inside it.

## Hard rules

- **The ratchet turns one way.** The profile tightens the open default; it never loosens it, and it never raises the `CLAUDE.md` security hard line.
  Active security testing stays forbidden no matter what the engagement "allows" — that's a different engagement entirely.
- **Per-dimension, not per-tier.** The reference profiles are shorthand; the real output is seven independent settings. Never collapse the answer to a
  single label and skip the dimensions the label glosses over.
- **The reason is load-bearing.** Each narrowed dimension records _why_ (contractual, legal, data-governance). A rule without a reason gets quietly
  dropped the first time it's inconvenient; the reason is what survives.
- **Stakeholder decisions, not inferred.** The envelope is asked, not grepped. A private repo or an `*.internal` URL is a _hint_ to confirm, never the
  whole answer — the LLM cannot read an NDA off the filesystem.
- **The appendix is tracked and team-shared.** The engagement envelope binds everyone on the suite, so `CLAUDE.profile.md` is committed (unlike the
  per-machine, gitignored `CLAUDE.local.md`). It describes _latitude_, never secrets — "real PII, redact screenshots", not the PII itself.
- **When unset, default to open _and say so_.** A dimension the user doesn't restrict stays at the Holy Book default — but list it under "Unchanged"
  so the openness is a recorded decision, not an oversight. The one exception is data sensitivity: if you genuinely can't tell whether data is real,
  treat it as real until told otherwise (the failure mode is a leak, and the safe side is restriction).

## When to run this skill

- At the **start of any engagement that isn't the open public-demo case** the Holy Book assumes — before `setup-environment` finishes assembling
  `CLAUDE.md`, or immediately after, so the suite's context carries the right envelope from the first action.
- When the user signals a restriction on this SUT: _"you can't probe / can't read the source / can't go on the web / can't touch prod / need sign-off
  / it's under NDA / that's real customer data."_
- Onboarding onto a **client or internal app** (as opposed to a throwaway demo).
- Before reaching for a latitude-assuming skill on an unprofiled SUT — `write-a-probe`, `assess-ecosystem`, the source-reading rules — when you're not
  sure the engagement grants it.
- **Re-run when the engagement's terms change**: SUT moves staging → prod, demo data becomes real data, an NDA lands, the repo goes private, security
  scope is added or withdrawn. Regenerate the appendix and re-run `setup-environment` Step 7.

## What this skill does NOT do

- It does not loosen anything. No setting it produces grants more latitude than the Holy Book default; the security hard line is untouchable. (See the
  invariant.)
- It does not assemble `CLAUDE.md`. It writes the `CLAUDE.profile.md` appendix; `setup-environment` Step 7 concatenates it. The split mirrors the
  adapter appendix: the source files are separate, the assembly is one step.
- It does not handle secrets or per-machine paths. Those are `CLAUDE.local.md`'s job (gitignored). The profile records _sensitivity and rules_, never
  credentials or paths.
- It does not map SUT parallel-safety bounds — that's `understand-sut-constraints`. Profiling is about _granted latitude_; constraints are about
  _technical limits_. A confidential SUT can still have a session cap, and vice versa.
- It does not infer the envelope from the codebase. It surfaces hints and asks; the answers are the stakeholder's, not the repo's.
- It does not decide test coverage, write tests, or run them. It sets the envelope those activities then operate inside; the downstream skills do the
  work, now bounded.
- It does not modify CI, the SUT, or any latitude-assuming skill's body. It governs them at runtime via the emitted rules — the skills stay generic;
  the profile is what narrows them for this engagement.
