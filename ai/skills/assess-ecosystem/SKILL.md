---
name: assess-ecosystem
description:
  "**Stalk the ecosystem** — go read what the wider internet says about the SUT, its dependencies, and the third-party technologies the test suite
  leans on, so the project's view of its own environment widens beyond the repo. Pulls from public docs (Selenium, Chrome / Firefox release notes,
  Heroku platform docs, the SUT's upstream repo, framework release notes), blog posts / Stack Overflow / GitHub issues that mention the SUT or a
  load-bearing dependency, and similar public testbeds. Produces an **ecosystem map** — what's out there, what's load-bearing on this project, what
  might be re-usable (a published selector list, a known-quirk catalogue, an upstream issue that explains a flake). The depth is **bounded by a token
  budget**, not by a page count: at invocation, estimate the remaining context-window tokens and allocate a fraction (default **1/3**) to the
  assessment; stop fetching when that budget is spent. Use whenever the user asks to scan the ecosystem, look for prior art, find upstream context for
  a flake, check what other people say about CURA / Selenium / Heroku / a specific Chrome version, or onboard onto a new technology in the stack.
  Never confuse what an external source claims with what the SUT actually does — the empirical-verification rule still owns the truth."
---

# Assess the ecosystem — bounded public-research pass

A **stalking** skill. Read the public internet around the SUT and the stack so the project's mental model isn't limited to its own repo: upstream
docs, third-party issue trackers, release notes, public discussions. Map what's out there, mark what's load-bearing on **this** project, surface what
might be re-usable (a documented selector list, a known quirk, an upstream bug that already explains a flake).

This is **assessment**, not verification. External sources widen the lens; they don't decide what's true about the SUT. Anything load-bearing still
needs the `empiricism` motion before it shapes a test.

## The token budget — bound the work explicitly

The web is unbounded. The budget is the only thing keeping this skill from downloading half the internet.

### How to set the budget

1. **At invocation, estimate remaining context-window tokens.** Default heuristic: assume the model's full window minus the visible-conversation
   footprint so far. If you can't estimate, default to **30% of the model's nominal window**.
2. **Allocate a fraction** — default **1/3** of remaining tokens for the whole assessment (all fetches + reading + producing the map). The user can
   override: `1/2`, `1/4`, an absolute cap like `30k tokens`.
3. **Plan fetches against the budget.** A typical WebFetch of a docs page lands in the 2k–10k-token range; a Stack Overflow thread, 1k–5k; a GitHub
   issue, 1k–8k. Build a **fetch shortlist** sized to fit, with priority order.
4. **Stop when the budget is spent.** Surface what you have. Don't keep fetching past the cap — the user invoked with a bound on purpose.

State the budget at the top of the map: _"Allocated ~20k tokens (1/3 of estimated remaining); spent ~17k across 6 fetches."_

### When to widen / narrow

- **Narrow** if the user said "quick scan" / "short", or the question is tightly scoped ("what does Chrome release-note say about BFcache in v131?").
  Drop to **1/4** or an absolute small cap.
- **Widen** if the user said "thorough" / "deep dive" and you have plenty of context. Up to **1/2**. Don't exceed half — leave room for the _use_ of
  the findings afterwards.
- **Hard cap regardless**: if a single fetch is going to blow more than **20%** of the allocated budget, skip it or summarize the URL rather than
  inhaling the page.

## What to look for — eight ecosystem surfaces

For each surface, decide before fetching: _is this load-bearing on this project?_ If yes — include in the shortlist. If incidental — note in the map
without fetching.

### 1. The SUT's upstream

Where does the SUT live? For CURA: `github.com/katalon-studio/katalon-demo-cura`. Read:

- The README / wiki — anything CURA-team says about _intended_ behaviour (vs the deployed app).
- Open + closed issues — bugs others have filed, especially around the same gaps your project tracks.
- The PHP source layout — what files are deployed, what endpoints exist beyond the form-rendered ones.
- Commit history — recent fixes that might explain a gap flipping resolved.

The SUT's upstream often confirms or refutes `IDENTIFIED_GAPS.md` entries: if a §9 gap matches an open upstream issue, that's external corroboration.

### 2. Selenium + WebDriver protocol

Release notes, behavioural change notes between versions:

- `selenium.dev/documentation/webdriver/` for current behaviour.
- The `seleniumhq/selenium` GitHub release notes — especially around `expected_conditions`, `Keys`, `Options`, BiDi.
- W3C WebDriver spec when a question is "what should the protocol do here?".

Useful when a probe behaves differently across Selenium versions, or when a wait condition's semantics are load-bearing.

### 3. Browser release notes

Chrome, Firefox. The release notes are where BFcache, autoplay, password-manager, and security-context changes land:

- `chromereleases.googleblog.com` and the Chromium status / feature flags pages.
- `firefox-source-docs.mozilla.org` and Mozilla's release notes.

Critical when a cross-browser finding (`§B-BROWSER-1`) might be explained by a documented browser change rather than a SUT quirk.

### 4. Hosting / infra platform

For CURA: Heroku. Read:

- Heroku's eco / free-tier docs — dyno sleep behaviour, request timeouts, concurrency limits.
- Heroku's incident history for the platform region.

`§A-ENV-1` (rapid-POST contention on a shared eco dyno) is exactly the kind of finding that Heroku docs can confirm — _yes, eco dynos serialize this
way under load._

### 5. Test framework / harness

Ocarina lives at `<gitignored>/ocarina` (per the memory). Public docs / repo:

- The Ocarina README / docs if public.
- Issue tracker if public — quirks others ran into.

This surface is small for proprietary frameworks; for popular ones (pytest, Playwright, Cypress) it's huge.

### 6. Public discussion of the SUT

People talk about CURA on the internet. Search:

- Stack Overflow for `katalon-demo-cura` or `katalon cura`.
- GitHub for repos that fork / import CURA tests — they may have already discovered selectors, gaps, flakes.
- Blog posts / tutorials — Katalon's own tutorials, third-party walkthroughs.

This is where **re-usable artifacts** live: a published selector list, an already-mapped form flow, a community-noted gap.

### 7. Third-party libraries the test suite imports

For the project: `selenium`, `pytest` (if used downstream), `ruff`, `mypy`. Each one has:

- Versioned release notes.
- Migration guides for major versions.

Useful when a CI break correlates with a library bump.

### 8. Adjacent / similar testbeds

Other public demo apps in the same family:

- Sauce Demo, ParaBank, the-internet (Heroku), automation-practice.
- Patterns from those projects sometimes transfer (e.g. "the-internet" has documented BFcache examples).

Cross-pollination — if another testbed solved the same problem, the solution shape is worth a glance.

## Procedure

### Step 1 — Restate the question

"Map the ecosystem around CURA generally." Or "find upstream context for the BFcache cross-browser finding." Or "what does Selenium 4.x say about
`element_to_be_clickable` that might explain the post-modal flake?" Or "onboard onto Heroku eco dyno behaviour."

Narrow questions get tight budgets and tight shortlists. Broad questions get the default 1/3.

### Step 2 — State the budget

One line. _"Allocating 1/3 of remaining tokens (≈20k) to this pass; cap per fetch ~4k tokens."_

If the user gave an explicit fraction or cap, use theirs.

### Step 3 — Build the fetch shortlist

Walk the eight surfaces. For each: _load-bearing on this project? worth a fetch within the budget?_ Produce an ordered list:

```markdown
Shortlist (in priority order, est. tokens):

1. github.com/katalon-studio/katalon-demo-cura README + open issues — ≈6k
2. Chrome release notes around BFcache (v124–v132 range) — ≈5k
3. Heroku eco-dyno docs (request handling, concurrency) — ≈3k
4. Stack Overflow `katalon-demo-cura` tag — ≈2k
5. Selenium 4.x expected_conditions docs — ≈2k

Total est: ~18k / 20k budget. OK.
```

Surface the shortlist before fetching anything heavy. The user can prune / reorder.

### Step 4 — Fetch within the budget

Use `WebFetch` for known URLs. Use `WebSearch` for "find me what people say about X". One fetch at a time; after each, update the spent count:

```
Spent: ~6k / 20k after upstream repo fetch. Continuing.
```

If a fetch overshoots its estimate by >2x, stop and reassess — the page may be a dump and not worth the cost.

### Step 5 — Note observations as you go

For each fetched source, capture in 2–4 bullets:

- **What it says** (one sentence).
- **Whether it's load-bearing** on this project (one phrase).
- **What it could re-use / confirm / refute** (one phrase).
- **URL** for citation.

Don't transcribe the source. The map needs _findings_, not pages.

### Step 6 — Surface the ecosystem map

Use this exact template:

```markdown
# Ecosystem map — <one-line question>

## Budget

- Allocated: ~<N>k tokens (<fraction> of estimated remaining).
- Spent: ~<M>k tokens across <K> fetches.
- Surfaces visited: <list>.
- Surfaces skipped (with reason): <list>.

## Findings

### SUT upstream (`<repo URL>`)

- <observation>. <load-bearing? what it could re-use / confirm / refute>.

### Browser (Chrome / Firefox release notes)

- <observation>. <…>.

### Hosting (Heroku)

- <observation>. <…>.

### Selenium / WebDriver

- <observation>. <…>.

### Public discussion of <SUT>

- <observation>. <…>.

### Adjacent testbeds

- <observation>. <…>.

## Re-usable artifacts found

- <a published selector list / a documented gap / an upstream issue that matches §9.X> — at <URL>.
- <…>.

## Cross-references to existing project artifacts

- `IDENTIFIED_GAPS.md` §<ref> — corroborated / contradicted by <finding>.
- `CURA_FRD.md` §<ref> — context added by <finding>.
- `CLAUDE.md` rule on <topic> — supported / could be tightened by <finding>.

## Open follow-ups (not pursued — budget bounded)

- <surface or URL not fetched, and why> — pick up next pass if relevant.

## Verdict

<one-line: ecosystem is well-aligned / one notable misalignment / a re-usable artifact worth pulling in / nothing material>.
```

Print the map. Do not write it to a file unless the user asks.

### Step 7 — Stop. The user decides.

The map is the artifact. Findings load-bearing on a test still need the `empiricism` motion before they reshape an assertion. The user picks:

- **Pull a re-usable artifact in** — cite the URL in a POM comment / `IDENTIFIED_GAPS.md` entry.
- **Re-verify a contradiction empirically** — invoke `empiricism` / `write-a-probe`.
- **Defer** — the finding is interesting but not actionable this pass.
- **Widen** — run the skill again with a larger budget / a narrower question.

The audit doesn't apply findings. It maps them.

## Hard rules

- **External claims are not SUT truth.** A Stack Overflow answer saying "CURA does X" is a _hypothesis_; the empirical verification rule (`CLAUDE.md`
  → "Verify SUT behaviour") still owns the answer.
- **Never fetch with attack-shape inputs.** Per `CLAUDE.md` → "Security testing is functional and static — never active". A Google search for
  `site:exploit-db.com cura` is out of scope; a search for `site:github.com katalon-demo-cura issues` is fine.
- **Cite every load-bearing finding.** A finding without a URL is a rumour. The map is only useful if the next reader can re-open the source.
- **Respect the budget.** If you've spent 90% and the last item is a 10k-page dump, stop. Note it as a follow-up; don't blow through.
- **Don't auto-edit project files.** The map surfaces; the user (or a follow-up skill invocation) applies.

## When to run this skill

- The user asks: "what does the internet say about X?", "scan the ecosystem", "find upstream context for this flake", "are there public selector lists
  for CURA?", "onboard me onto Heroku eco dynos".
- A new third-party dependency lands in `pyproject.toml` — what's its quirk catalogue?
- A `review-suite-stability` audit surfaces a flake with no internal explanation — widen to see if anyone outside has hit it.
- A `B-BROWSER-*` entry could be explained by a documented browser change — check the release notes.
- Onboarding — give a contributor the external map alongside the internal `assess-test-base` catalog.

## What this skill does NOT do

- It does not run probes against the SUT. (That's `write-a-probe`.)
- It does not update `IDENTIFIED_GAPS.md` / `CURA_FRD.md` / POM comments. (Those are user-driven follow-ups, via `update-frd-and-tests` etc.)
- It does not fetch unbounded — the token budget is the bound. Default 1/3 of remaining; never more than 1/2.
- It does not run security scanners, vulnerability tools, or active probes against external services. Public docs + public discussions only.
- It does not summarize entire pages into the map. The map captures _findings_; the URLs let the next reader re-open the source.
- It does not pretend an external claim is SUT truth. Empirical verification still owns that.
