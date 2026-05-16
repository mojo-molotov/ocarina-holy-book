---
name: understand-ocarina
description:
  "**Deep-comprehension skill for Ocarina — the test framework an Ocarina suite is built on.** The primary source of LLM-oriented Ocarina
  documentation is the **Ocarina Holy Book**, publicly hosted at `http://mojo-molotov.github.io/ocarina-holy-book` once published. The skill fetches
  the Holy Book's pages directly when the site is reachable; if it isn't (not yet published, offline, redirect failure), the skill **clones** the Holy
  Book source repo, builds it locally, and reads the built artifacts. Secondary sources — the Ocarina source clone (`<gitignored>/ocarina/`), the
  Ocarina example clone (`<gitignored>/ocarina-example/`), and the AI-proof example (`<gitignored>/ocarina-with-ai-example/`) — supplement the Holy
  Book for code-level questions the docs don't cover. Use whenever the user asks to understand Ocarina, look up a framework primitive (TestChain,
  drive_page, match_page, Watcher, fragments, scenarios, suites, campaigns, cycles), audit a project's Ocarina usage, or onboard onto the framework.
  The skill answers the *framework* question; project-specific questions (POMs, scenarios in the project root) are out of scope — those are covered by
  `assess-test-base`."
---

# Understand Ocarina — start with the Holy Book

A comprehension skill. Ocarina is the framework an Ocarina suite is built on; understanding its primitives, conventions, and contracts is a
prerequisite for most authoring and review motions. The skill walks the documentation tiers, in priority order, until the question is answered.

## The documentation tiers

### Tier 1 — Ocarina Holy Book (LLM-oriented, public)

The canonical LLM-facing documentation, hosted at:

```
http://mojo-molotov.github.io/ocarina-holy-book
```

(Adapt if the live URL has changed — verify with the user before reverting to a cached or alternate location. The URL above is the documented public
home at the time this skill was authored.)

The Holy Book is **the primary source** when reachable. It's structured for LLM consumption: page-per-concept, examples, type signatures, contracts.

**Reach via `WebFetch`** for specific pages once the page-list is known. Use `WebSearch` only when looking for a concept whose page name is unknown.

### Tier 2 — Holy Book repo (cloned + built locally, when Tier 1 unreachable)

When the public site isn't reachable (DNS / not-yet-published / offline / 404), fall back to the source repo. The skill **clones, builds, and reads**
the built artifacts locally.

Standard local home (proposed, confirm with user before creating):

```
<gitignored>/ocarina-holy-book/
```

Build steps depend on the repo's static-site generator (Hugo / MkDocs / Docusaurus / etc.) — read the repo's README on first clone, follow its build
instructions. **Do not assume a build system**; read first.

### Tier 3 — Ocarina source clone (`<gitignored>/ocarina/`)

For questions the Holy Book doesn't answer — internals, undocumented edge cases, type-level details, decorator chains. The source is the ultimate
authority on behaviour but the worst authority on intent (the Holy Book is for intent).

Already present per memory:

- `<gitignored>/ocarina` — the Ocarina source.
- `<gitignored>/ocarina-example` — minimal example project showing canonical patterns.
- `<gitignored>/ocarina-with-ai-example` — richer example project (gap inventory, AI proof, dispatcher dataset, full cycle).

### Tier 4 — Ocarina-example clones (`<gitignored>/ocarina-example/`, `<gitignored>/ocarina-with-ai-example/`)

Canonical reference for _how to use_ the primitives, not just what they are. When the Holy Book describes a concept abstractly and you need the
working shape, the example clones are the canonical _shape_ source. `ocarina-example` is the minimal demo; `ocarina-with-ai-example` is the richer
project with a gap inventory and AI-friendly conventions.

## The lookup priority

For any Ocarina question:

1. **Check whether the answer is already in this conversation / `CLAUDE.md`** — silent if yes.
2. **Try Tier 1** (Holy Book, online). Fetch the relevant page.
3. **If Tier 1 unreachable** — clone (or update existing clone of) the Holy Book repo, build, read the built pages.
4. **If Holy Book lacks the answer** — Tier 3 (Ocarina source) for behaviour, Tier 4 (example) for shape.
5. **If still unanswered** — surface the gap explicitly. _"The Holy Book and source clones don't answer X; the question may need to go to the Ocarina
   maintainers."_

Don't skip tiers without reason. The Holy Book is the LLM-optimised target; jumping straight to grep'ing source loses the structured framing the docs
provide.

## Procedure

### Step 1 — Frame the question

"How does `match_page` work?" — concept lookup, Tier 1 first. "What's the exact signature of `TestScenarioFragment`?" — Tier 1, fall to Tier 3 if
needed. "What's a canonical Watcher callback shape?" — Tier 4 (example clones) primarily, Tier 1 for the abstract framing. Prefer `ocarina-example`
for the simplest shape, `ocarina-with-ai-example` for the richer demonstration.

Narrow questions need targeted fetches; broad questions ("walk me through Ocarina's test hierarchy") may need a page or two of the Holy Book.

### Step 2 — Try Tier 1 (Holy Book online)

```text
WebFetch: http://mojo-molotov.github.io/ocarina-holy-book/<page-or-section>
```

If the page doesn't exist or the site is unreachable, capture the failure mode (DNS failure, 404, redirect chain) — that decides whether Tier 2 is
needed or whether a different page name is the issue.

If the structure of the Holy Book is unknown (first invocation, or the layout changed), fetch the index / sitemap first:

```text
WebFetch: http://mojo-molotov.github.io/ocarina-holy-book/
WebFetch: http://mojo-molotov.github.io/ocarina-holy-book/sitemap.xml
```

Use the index to find the right page; then fetch.

### Step 3 — Fall to Tier 2 (Holy Book cloned + built) if Tier 1 unreachable

The repo URL isn't certain at skill-authoring time — likely `https://github.com/mojo-molotov/ocarina-holy-book` based on the published URL, but
**confirm with the user before cloning**. The skill never clones unconfirmed repos unilaterally.

Once confirmed:

```bash
# Clone if absent
git clone <repo URL> <gitignored>/ocarina-holy-book

# Or update if present
cd <gitignored>/ocarina-holy-book && git pull && cd -

# Read the README for build instructions
cat <gitignored>/ocarina-holy-book/README.md

# Build per the README (Hugo / MkDocs / Docusaurus / etc.)
# Then read the built pages
```

Read the built artifacts (commonly `site/`, `public/`, `build/`) — those are the LLM-oriented pages. The raw source markdown may also be usable; the
_built_ form is preferred because it matches what the public site would serve.

### Step 4 — Fall to Tier 3 / 4 (source / example clones) if Holy Book lacks the answer

```bash
ls <gitignored>/ocarina
ls <gitignored>/ocarina-example
ls <gitignored>/ocarina-with-ai-example
```

All three should be present per the local-clones memory. If any are absent, surface the gap and ask the user before cloning (the URLs are not
unilaterally confirmed by this skill).

`grep` for the symbol; `Read` for the file:

```bash
grep -rn "<symbol>" <gitignored>/ocarina/src
grep -rn "<symbol>" <gitignored>/ocarina-example
grep -rn "<symbol>" <gitignored>/ocarina-with-ai-example
```

### Step 5 — Synthesise the answer

For any answer, capture:

- **Source tier(s) used** — Holy Book (page URL) / source (file:line) / example (file:line).
- **The contract** — type signature, lifecycle, exceptions, side effects.
- **The shape** — a minimal working example (from the example clone, or sketched from the Holy Book).
- **Cross-references** — related skills in the project that touch the same primitive.

The synthesis is the deliverable; the raw fetches are scaffolding.

### Step 6 — Surface the answer

````markdown
# Ocarina comprehension — `<question in one sentence>`

## Tier(s) consulted

- Tier 1 (Holy Book online): <page URL | "unreachable: <reason>">.
- Tier 2 (Holy Book cloned): <built page path | "not needed" | "fell back, built at <path>">.
- Tier 3 (Ocarina source): <file:line | "not needed">.
- Tier 4 (Ocarina example clones): <file:line | "not needed">.

## Answer

<one to several paragraphs synthesising the contract, the shape, and the cross-references>

## Working shape (when applicable)

```python
<minimal example, ideally from <gitignored>/ocarina-example or sketched from the Holy Book>
```
````

## Cross-references

- Related skills: `<list>` (e.g. `analyse-watcher-flakiness` for Watcher questions, `refactor-fragmentation` for TestScenarioFragment, etc.).
- `CLAUDE.md` rule on `<topic>` if applicable.

## Open follow-ups

- <if any aspect is unanswered or ambiguous — surface explicitly>.

```

Print the answer. The Holy Book pages can be cached locally as Tier 2 build, but **don't** copy Holy Book content into project files —
cross-reference URLs instead, so the canonical source stays canonical.

### Step 7 — Stop. The user picks the next motion.

The comprehension is the deliverable. Acting on the answer (extending coverage, refactoring a POM to use a primitive correctly, auditing a watcher) is
a different motion handled by another skill.

## Hard rules

- **Tier order matters.** Holy Book first when reachable; only fall through when the tier above doesn't answer. Skipping tiers loses structured
  framing.
- **Never assume the build system of the Holy Book repo.** Read its README first; build per its instructions.
- **Never clone unconfirmed repos unilaterally.** The skill confirms the URL with the user before cloning the Holy Book (or any new repo). The
  existing Ocarina / `ocarina-example` / `ocarina-with-ai-example` clones are already in memory; those are pre-confirmed.
- **Cite tier + location for every load-bearing claim.** Holy Book URL, source file:line, example file:line. A claim without a citation can't be
  re-verified.
- **Don't copy Holy Book content into project files.** Cross-reference URLs. The Holy Book is the canonical source; mirroring it in the project root makes
  stale copies inevitable.
- **The Holy Book URL is `http://mojo-molotov.github.io/ocarina-holy-book` per the skill's authoring date.** If unreachable consistently, the URL may
  have moved — verify with the user before assuming the URL is broken vs the site is unpublished.
- **Per `CLAUDE.md`: security testing is functional and static — never active.** Web fetches stay on the documentation domain; no exploration
  beyond the Holy Book and the confirmed source repos.
- **Don't extend coverage or refactor as part of this skill.** Comprehension only; acting on the answer is a separate motion.
- **`reference_ocarina_repos.md` memory may be stale.** Verify the clones are still at the documented paths before reading; re-clone if missing.

## When to run this skill

- A skill (this one or another) needs an Ocarina contract precisely (signature, lifecycle, exception behaviour) and the answer isn't already in
  `CLAUDE.md`.
- A contributor asks "how does Ocarina do X?" — the Holy Book is the starting point.
- After an Ocarina version bump — re-verify contracts that changed.
- Before authoring a new POM / scenario that uses an unfamiliar primitive — comprehension first, authoring second.
- During flakiness investigations when the primitive's behaviour (Watcher daemon timing, retry contract, transient classifier) is load-bearing.

## What this skill does NOT do

- It does not author code that uses the Ocarina primitive. Comprehension only; authoring is `extend-coverage` / `empiricism` / direct edit.
- It does not modify Ocarina source. The source clones are read-only references.
- It does not commit clones (the `<gitignored>/` path is gitignored by project convention).
- It does not mirror Holy Book content into the project. Cross-references the URL.
- It does not build the Holy Book unless Tier 1 is unreachable. Building is the fallback, not the default.
- It does not unilaterally clone repos. Confirms with the user before any new clone (Ocarina / `ocarina-example` / `ocarina-with-ai-example` are
  already in memory; the Holy Book repo is not yet confirmed at the skill's authoring date).
- It does not include attack-shape questions in any Holy Book / source query. Per `CLAUDE.md` → "Security testing is functional and static —
  never active".
```
