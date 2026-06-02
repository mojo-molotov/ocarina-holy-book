---
name: understand-ocarina
description:
  "**Deep-comprehension skill for Ocarina — the test framework an Ocarina suite is built on.** Two complementary public doc sites lead. For
  *reference* questions — a primitive's signature, contract, lifecycle (TestChain, drive_page, match_page, Watcher, fragments, scenarios, suites,
  campaigns, cycles) — the primary source is the **Ocarina Holy Book** (`http://mojo-molotov.github.io/ocarina-holy-book`). For *intent / cartography
  / philosophy / cross-repo* questions — why the framework is shaped the way it is, how the six ecosystem repos relate, the Railway/functional design
  rationale, CI/CD across the ecosystem — the primary source is the book **from-ocarina-to-igor**
  (`https://mojo-molotov.github.io/from-ocarina-to-igor/`), a chaptered reverse-engineering of the whole ecosystem. The skill fetches either site
  directly when reachable; if a site isn't (unpublished, offline, redirect failure), it **clones** that repo, builds it locally (both are Hugo), and
  reads the built artifacts. Secondary sources — the Ocarina source clone (`<gitignored>/ocarina/`) plus the worked-example clones (`ocarina-example`
  and `ocarina-with-ai-example` for the **Selenium** adapter, `ocarina-with-playwright-example` for the **Playwright** adapter) — supplement the docs
  for code-level questions and canonical shape. Use whenever the user asks to understand Ocarina, look up a framework primitive, grasp the ecosystem
  or design intent, audit a project's Ocarina usage, or onboard onto the framework. The skill answers the *framework* question; project-specific
  questions (POMs, scenarios in the project root) are out of scope — those are covered by `assess-test-base`."
---

# Understand Ocarina — start with the two doc sites

A comprehension skill. Ocarina is the framework an Ocarina suite is built on; understanding its primitives, conventions, contracts, and design intent
is a prerequisite for most authoring and review motions. Two public doc sites lead — the **Holy Book** for reference (what a primitive is) and the
book **from-ocarina-to-igor** for intent and ecosystem cartography (why it's shaped this way) — backed by the Ocarina source and the adapter-matched
worked examples. The skill routes to the right source by the question, then falls through to source/examples only when the docs don't answer.

## The documentation tiers

Two public doc sites are the primary surface; they answer **different classes of question** and you route by the question, not by a fixed order:

- **Reference — _what_ a primitive is** (signature, contract, lifecycle, exceptions): the **Holy Book** (Tier 1).
- **Intent / cartography / philosophy — _why_ Ocarina is shaped this way, _how the ecosystem fits together_** (repo relations, Railway/functional
  design rationale, ecosystem-wide CI/CD, tester independence): the **book `from-ocarina-to-igor`** (Tier 1B).

Many real questions touch both ("how does `match_page` work _and why does it retry the way it does_"): get the contract from the Holy Book and the
rationale from the book. Below each primary site is its own clone-and-build fallback; the source and example clones sit beneath both.

### Tier 1 — Ocarina Holy Book (LLM-oriented reference, public)

The canonical LLM-facing **reference**, hosted at:

```
http://mojo-molotov.github.io/ocarina-holy-book
```

(Adapt if the live URL has changed — verify with the user before reverting to a cached or alternate location. The URL above is the documented public
home at the time this skill was authored.)

The Holy Book is **the primary source for reference questions** when reachable. It's structured for LLM consumption: page-per-concept, examples, type
signatures, contracts.

**Reach via `WebFetch`** for specific pages once the page-list is known. Use `WebSearch` only when looking for a concept whose page name is unknown.

### Tier 1B — the book `from-ocarina-to-igor` (intent, cartography, philosophy, public)

A chaptered reverse-engineering of the **whole Ocarina ecosystem** — the companion to the Holy Book's per-primitive reference. Hosted at:

```
https://mojo-molotov.github.io/from-ocarina-to-igor/
```

This is **the primary source for the _why_** — design intent, the six-repo cartography, the functional/Railway rationale, ecosystem-wide CI/CD, the
philosophy of tester independence. It's a Hugo + hugo-book site (EN default, FR via the language switcher) with Pagefind search (`⌘K` / `Ctrl+K`). The
chapter map, useful for targeting a `WebFetch`:

| Chap. | Subject                                                     |
| :---: | ----------------------------------------------------------- |
|  00   | Big picture: cartography, execution flow, repo relations    |
|  01   | Philosophy of Igor Casanova                                 |
|  02   | The Ocarina framework, internal mechanics                   |
|  03   | Functional programming with Ocarina (Effect, Thunk, Result) |
|  04   | Internal tests of the framework                             |
|  05   | The Igoristan (public SUT)                                  |
|  06   | `tests-workers` (Vercel Edge backend)                       |
|  07   | `ocarina-example` (canonical Selenium suite)                |
|  08   | `ocarina-with-ai-example` (AI-co-authored suite)            |
|  09   | The Holy Book (docs + AI skills)                            |
|  10   | CI/CD across the whole ecosystem                            |
|  11   | The independence of testers                                 |
|  12   | The manifesto, deciphered                                   |
|  99   | Glossary, file index                                        |

**Reach via `WebFetch`** at `https://mojo-molotov.github.io/from-ocarina-to-igor/<NN-folder>/` once the chapter is known; `WebSearch` (or the live
`⌘K` Pagefind index) when the chapter is unknown. The folder slugs match the table (`00-big-picture/`, `03-functional/`, …).

### Tier 2 — doc-site repos (cloned + built locally, when Tier 1 / 1B unreachable)

When a public site isn't reachable (DNS / not-yet-published / offline / 404), fall back to **that site's** source repo. The skill **clones, builds,
and reads** the built artifacts locally. The fallback is per-site: a 404 on the Holy Book doesn't mean the book is down too.

Standard local homes (proposed, confirm with user before creating):

```
<gitignored>/ocarina-holy-book/        # Holy Book repo  (mojo-molotov/ocarina-holy-book)
<gitignored>/from-ocarina-to-igor/     # the book repo   (mojo-molotov/from-ocarina-to-igor)
```

Both are **Hugo + hugo-book** sites: the book builds via its `site/build.sh` (Hugo with minification + a Pagefind index via `npx`); confirm the Holy
Book's generator from its README rather than assuming it matches. Either way, **read the repo's README on first clone and follow its build
instructions** — don't assume the build invocation. Read the built artifacts (commonly `site/`, `public/`, `build/`); the built form is preferred
because it matches what the public site serves.

### Tier 3 — Ocarina source clone (`<gitignored>/ocarina/`)

For questions the docs don't answer — internals, undocumented edge cases, type-level details, decorator chains. The source is the ultimate authority
on behaviour but the worst authority on intent: for the _why_, the book (Tier 1B, esp. chapters 02/03) is the deliberate explanation; the source only
shows the _what_.

Already present per memory:

- `<gitignored>/ocarina` — the Ocarina source.
- `<gitignored>/ocarina-example` — minimal Selenium example showing canonical patterns.
- `<gitignored>/ocarina-with-ai-example` — richer Selenium example (gap inventory, AI proof, dispatcher dataset, full cycle).
- `<gitignored>/ocarina-with-playwright-example` — the Playwright worked example (same suite as `ocarina-example`, Selenium backend swapped for
  Playwright). May not yet be in the clones memory — see the Tier-4 note.

### Tier 4 — worked-example clones (per adapter)

Canonical reference for _how to use_ the primitives, not just what they are. When the docs describe a concept abstractly and you need the working
shape, the example clones are the canonical _shape_ source. **The right example depends on the project's driver adapter** (the `Adapter:` line in
`CLAUDE.local.md` — Ocarina is adapter-shaped; see `CLAUDE.md` → "Driver adapter"):

- **Selenium** — `ocarina-example` (minimal demo) and `ocarina-with-ai-example` (richer project, gap inventory, AI-friendly conventions).
- **Playwright** — `ocarina-with-playwright-example`. A fork of `ocarina-example` that swaps only the framework-coupling layer
  (`create_playwright_test`, string locators with auto-wait, `driver.submit(lambda page: …)` thread-marshalling, `--browser chromium|firefox|webkit`
  and no `--driver-path`). The test logic — page objects, scenarios, suites, campaigns, the `e2e` cycle — is identical to the Selenium version, so
  it's the canonical place to see **what an adapter swap does and doesn't touch**.

When the question is adapter-neutral (hierarchy, scenario DSL, reporting), prefer the simplest example (`ocarina-example`). When it's adapter-specific
(how waits, locators, or submission differ), read the example matching the adapter in play — and the matching `CLAUDE.<adapter>.md` appendix.

> **Naming note.** The Playwright example's canonical repo is `mojo-molotov/ocarina-with-playwright-example`. The older URL
> `…/ocarina-with-playwright` (as still linked in `CLAUDE.md`) 301-redirects to it — same repo, stale name. Clone the canonical name.

## The lookup priority

For any Ocarina question:

1. **Check whether the answer is already in this conversation / `CLAUDE.md`** — silent if yes.
2. **Pick the primary site by question class.** Reference (what a primitive is) → **Tier 1**, the Holy Book. Intent / ecosystem / philosophy (why, how
   the repos relate) → **Tier 1B**, the book. Fetch the relevant page/chapter. A question that has both halves consults both.
3. **If the chosen site is unreachable** — clone (or update the existing clone of) _that_ repo, build, read the built pages (Tier 2).
4. **If the docs lack the answer** — Tier 3 (Ocarina source) for behaviour, Tier 4 (the adapter-matched example) for shape.
5. **If still unanswered** — surface the gap explicitly. _"The Holy Book, the book, and the source clones don't answer X; the question may need to go
   to the Ocarina maintainers."_

Don't skip tiers without reason. The two doc sites are the LLM-optimised targets; jumping straight to grep'ing source loses the structured framing —
the Holy Book's contracts and the book's rationale — that the docs provide.

## Procedure

### Step 1 — Frame the question

"How does `match_page` work?" — reference lookup, Tier 1 first. "What's the exact signature of `TestScenarioFragment`?" — Tier 1, fall to Tier 3 if
needed. "Why is the suite built on Railway Oriented Programming?" / "How do the six ecosystem repos relate?" — Tier 1B (the book), chapters 00/02/03.
"What's a canonical Watcher callback shape?" — Tier 4 (example clones) primarily, Tier 1 for the abstract framing; pick the example matching the
project's adapter (`ocarina-example` for the simplest Selenium shape, `ocarina-with-playwright-example` for Playwright).

Narrow questions need targeted fetches; broad questions ("walk me through Ocarina's test hierarchy") may need a page or two of the Holy Book; "give me
the lay of the land" questions are the book's job.

### Step 2 — Try the primary site online (Tier 1 and/or Tier 1B)

For a **reference** question, fetch the Holy Book; for an **intent / cartography** question, fetch the book; for a mixed question, both.

```text
WebFetch: http://mojo-molotov.github.io/ocarina-holy-book/<page-or-section>       # reference
WebFetch: https://mojo-molotov.github.io/from-ocarina-to-igor/<NN-folder>/        # intent / cartography
```

If the page doesn't exist or the site is unreachable, capture the failure mode (DNS failure, 404, redirect chain) — that decides whether Tier 2 is
needed or whether a different page name is the issue.

If the structure of a site is unknown (first invocation, or the layout changed), fetch the index / sitemap first:

```text
WebFetch: http://mojo-molotov.github.io/ocarina-holy-book/
WebFetch: http://mojo-molotov.github.io/ocarina-holy-book/sitemap.xml
WebFetch: https://mojo-molotov.github.io/from-ocarina-to-igor/        # then use the chapter table above
```

Use the index to find the right page; then fetch.

### Step 3 — Fall to Tier 2 (the unreachable site, cloned + built)

Clone only the site that's actually down — the repos are independent. **Confirm the repo URL with the user before cloning**; the skill never clones
unconfirmed repos unilaterally.

| Down site | Repo (confirm before cloning)       | Local home                           |
| --------- | ----------------------------------- | ------------------------------------ |
| Holy Book | `mojo-molotov/ocarina-holy-book`    | `<gitignored>/ocarina-holy-book/`    |
| The book  | `mojo-molotov/from-ocarina-to-igor` | `<gitignored>/from-ocarina-to-igor/` |

```bash
# Clone if absent (else: cd <home> && git pull && cd -)
git clone <repo URL> <local home>

# Read the README for build instructions, then build per it
cat <local home>/README.md
```

Both are Hugo + hugo-book; the book builds via its `site/build.sh`. Don't assume the invocation — read the README first. Read the built artifacts
(commonly `site/`, `public/`, `build/`); the _built_ form is preferred because it matches what the public site would serve.

### Step 4 — Fall to Tier 3 / 4 (source / example clones) if the docs lack the answer

```bash
ls <gitignored>/ocarina
ls <gitignored>/ocarina-example                  # Selenium
ls <gitignored>/ocarina-with-ai-example          # Selenium
ls <gitignored>/ocarina-with-playwright-example  # Playwright
```

The Ocarina source and the Selenium examples should be present per the local-clones memory; the Playwright example may not be yet. If any needed clone
is absent, surface the gap and ask the user before cloning (the URLs are not unilaterally confirmed by this skill).

`grep` for the symbol; `Read` for the file. Grep the example matching the project's adapter — there's no point reading Selenium `By.*` locators for a
Playwright project, or vice versa:

```bash
grep -rn "<symbol>" <gitignored>/ocarina/src
grep -rn "<symbol>" <gitignored>/ocarina-example                  # Selenium project
grep -rn "<symbol>" <gitignored>/ocarina-with-playwright-example  # Playwright project
```

### Step 5 — Synthesise the answer

For any answer, capture:

- **Source tier(s) used** — Holy Book (page URL) / the book (chapter URL) / source (file:line) / example (file:line).
- **The contract** — type signature, lifecycle, exceptions, side effects.
- **The rationale** — when the question asks _why_, the book's design intent (chapter URL), not a guess.
- **The shape** — a minimal working example (from the adapter-matched example clone, or sketched from the Holy Book).
- **Cross-references** — related skills in the project that touch the same primitive.

The synthesis is the deliverable; the raw fetches are scaffolding.

### Step 6 — Surface the answer

````markdown
# Ocarina comprehension — `<question in one sentence>`

## Tier(s) consulted

- Tier 1 (Holy Book, reference): <page URL | "unreachable: <reason>" | "not needed">.
- Tier 1B (the book, intent/cartography): <chapter URL | "not needed">.
- Tier 2 (site cloned + built): <which site, built page path | "not needed" | "fell back, built at <path>">.
- Tier 3 (Ocarina source): <file:line | "not needed">.
- Tier 4 (example clone, <adapter>): <file:line | "not needed">.

## Answer

<one to several paragraphs synthesising the contract, the shape, and the cross-references>

## Working shape (when applicable)

```python
<minimal example, ideally from the adapter-matched example clone or sketched from the Holy Book>
```
````

## Cross-references

- Related skills: `<list>` (e.g. `analyse-watcher-flakiness` for Watcher questions, `refactor-fragmentation` for TestScenarioFragment, etc.).
- `CLAUDE.md` rule on `<topic>` if applicable.

## Open follow-ups

- <if any aspect is unanswered or ambiguous — surface explicitly>.

```

Print the answer. The doc-site pages can be cached locally as a Tier 2 build, but **don't** copy Holy Book or book content into project files —
cross-reference URLs instead, so the canonical source stays canonical.

### Step 7 — Stop. The user picks the next motion.

The comprehension is the deliverable. Acting on the answer (extending coverage, refactoring a POM to use a primitive correctly, auditing a watcher) is
a different motion handled by another skill.

## Hard rules

- **Route by question class, not a fixed order.** Reference → Holy Book; intent/cartography/philosophy → the book. Within a class, only fall through to
  source/examples when the doc tier above doesn't answer. Skipping tiers loses structured framing.
- **Don't answer a _why_ from source alone.** The source shows behaviour, not intent — inventing a rationale from the code is exactly what the book
  exists to prevent. Cite the book's chapter, or say the intent is undocumented.
- **Never assume a doc repo's build system.** Both sites are Hugo + hugo-book today, but read the README first; build per its instructions.
- **Never clone unconfirmed repos unilaterally.** Confirm the URL with the user before cloning either doc site or any example. The existing Ocarina /
  `ocarina-example` / `ocarina-with-ai-example` clones are in memory and pre-confirmed; the book and `ocarina-with-playwright-example` may not be yet.
- **Cite tier + location for every load-bearing claim.** Holy Book URL, book chapter URL, source file:line, example file:line. A claim without a
  citation can't be re-verified.
- **Don't copy doc-site content into project files.** Cross-reference URLs. The Holy Book and the book are the canonical sources; mirroring them in the
  project root makes stale copies inevitable.
- **The doc-site URLs are `http://mojo-molotov.github.io/ocarina-holy-book` and `https://mojo-molotov.github.io/from-ocarina-to-igor/` per the skill's
  authoring date.** If one is unreachable consistently, it may have moved — verify with the user before assuming the URL is broken vs the site is
  unpublished.
- **Match the example to the adapter.** Read the Selenium examples for a Selenium project, `ocarina-with-playwright-example` for a Playwright one (the
  `Adapter:` line in `CLAUDE.local.md`). Reading the wrong-adapter example teaches the wrong locator/wait/submission shape.
- **Per `CLAUDE.md`: security testing is functional and static — never active.** Web fetches stay on the documentation domains; no exploration
  beyond the two doc sites and the confirmed source repos.
- **Don't extend coverage or refactor as part of this skill.** Comprehension only; acting on the answer is a separate motion.
- **`reference_ocarina_repos.md` memory may be stale.** Verify the clones are still at the documented paths before reading; re-clone if missing.

## When to run this skill

- A skill (this one or another) needs an Ocarina contract precisely (signature, lifecycle, exception behaviour) and the answer isn't already in
  `CLAUDE.md`.
- A contributor asks "how does Ocarina do X?" — the Holy Book is the starting point.
- A contributor asks "why is Ocarina built this way?" / "how do these repos fit together?" / "what's the philosophy here?" — the book is the starting
  point, and it's the right onboarding read for someone new to the whole ecosystem.
- After an Ocarina version bump — re-verify contracts that changed.
- Before authoring a new POM / scenario that uses an unfamiliar primitive — comprehension first, authoring second.
- During flakiness investigations when the primitive's behaviour (Watcher daemon timing, retry contract, transient classifier) is load-bearing.

## What this skill does NOT do

- It does not author code that uses the Ocarina primitive. Comprehension only; authoring is `extend-coverage` / `empiricism` / direct edit.
- It does not modify Ocarina source. The source clones are read-only references.
- It does not commit clones (the `<gitignored>/` path is gitignored by project convention).
- It does not mirror Holy Book or book content into the project. Cross-references the URL.
- It does not build a doc site unless its public site is unreachable. Building is the fallback, not the default.
- It does not unilaterally clone repos. Confirms with the user before any new clone (Ocarina / `ocarina-example` / `ocarina-with-ai-example` are
  already in memory; the book and `ocarina-with-playwright-example` may not be yet).
- It does not include attack-shape questions in any doc-site / source query. Per `CLAUDE.md` → "Security testing is functional and static —
  never active".
```
