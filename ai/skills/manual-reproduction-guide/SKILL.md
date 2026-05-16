---
name: manual-reproduction-guide
description:
  Produce a structured, step-by-step **manual reproduction guide** that a human can follow in a real browser to reproduce a behaviour, a bug, or a
  documented finding — **plus** the hypothesis-confirmation paths (DevTools, `curl`, PHP read, comparison to `IDENTIFIED_GAPS.md`) the user can run
  when their first observation is fuzzy — **plus**, when a cross-browser contrast is part of the finding, the same steps repeated in the contrasting
  browser with the differences called out. Use whenever the user asks to write a repro recipe, document a manual repro, capture a finding so a human
  can verify it, share a bug for review, or build the user-facing companion to a Selenium probe.
---

# Manual reproduction guide

A skill for producing the **human-runnable** companion to a finding. Selenium probes (`write-a-probe`) capture machine-driven evidence; `empiricism`
walks the verification loop; this skill produces the artifact a _human_ opens their own browser to follow.

Three layers, used in order. Layers 2 and 3 are optional.

1. **Step-by-step reproduction** — what the user clicks, types, observes. Numbered. Pristine.
2. **Hypothesis-confirmation paths** — when the first observation is fuzzy or ambiguous, the means to firm it up: DevTools panels to open, network
   requests to inspect, headers to read, source to consult.
3. **Cross-browser contrast** — only when the finding _is_ a cross-browser difference. Same steps in the other browser, the difference called out at
   the exact step it appears.

The guide is the artifact. It can be printed in chat, saved into an `IDENTIFIED_GAPS.md` entry as a "Confirmation recipe" block (the project already
uses this — see §B-BROWSER-1), or stored as a one-off in `<gitignored>/` if it's for a single session's investigation.

## When to use which layer

| Situation                                                                                            | Layers needed         |
| ---------------------------------------------------------------------------------------------------- | --------------------- |
| User wants a clean repro recipe to share / save (no diagnosis needed)                                | 1                     |
| Initial observation is fuzzy ("something weird happens") and the user wants the confirmation tooling | 1 + 2                 |
| The finding is a cross-browser difference (one browser does X, another does Y)                       | 1 + 3, optionally + 2 |
| Everything                                                                                           | 1 + 2 + 3             |

Pick before writing. Don't pad the guide with layers the finding doesn't need.

## Layer 1 — step-by-step reproduction

A numbered, terse, browser-driven sequence. Every step is one observable action or one expected observation. Skip Selenium concepts entirely — this
layer is for a human, not for the suite.

What every step needs:

- **What to do** — click, type, press, navigate. Use UI-visible labels (`"Make Appointment"`, `"Login"`, the hamburger icon `☰`), not internal IDs.
- **What to observe** — the URL bar, the page heading, the visible text, a button label. Specific enough that the user knows whether they've
  reproduced it or stumbled into something else.
- **The URL** at each navigation step — verbatim, including the fragment.

Standard template (mirror the shape used in `IDENTIFIED_GAPS.md` §B-BROWSER-1's manual recipe):

```markdown
## Manual reproduction

1. **Open** `<browser>`, navigate to `<URL>`.
2. **Log in** — username `<DEMO_USERNAME from src/constants/credentials.py>`, password `<DEMO_PASSWORD>`. (Both public.)
   - You land on `<URL>`, the form's header reads `<…>`.
3. **Navigate** to `<URL>`. You see `<concrete observation: a heading, a list, an empty-state message>`.
4. **Click** `<button label>` / **press** `<key>` / **type** `<input>` into the `<field label>` field.
5. **Observe** — URL bar reads `<URL>`, the page heading is `<…>`, …
6. … (continue, one observable per line)
```

Always include the URL at the top of each navigation step — that's the one observation a screen-share can't accidentally mislead you about.

Demo credentials are intentionally exposed in `src/constants/credentials.py` (CURA is a public demo). Cite the constants, don't hardcode the values,
so the guide stays in sync if those ever change.

## Layer 2 — hypothesis-confirmation paths

Add this layer only when the initial observation needs disambiguation — symptoms like "the page looks stale", "something didn't redirect", "the cookie
behaviour is unclear". The user has an initial impression; the layer gives them the tools to firm it up without writing a Selenium probe.

The confirmation tools, in order of cost (cheapest first):

| Tool                                                     | When                                                                          | How                                                                                                                                                       |
| -------------------------------------------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DevTools — Network tab**                               | "Did this navigation hit the server?" / "What did the server return?"         | F12 → Network → repeat the step. Inspect status, headers, response.                                                                                       |
| **DevTools — Application → Back/forward cache** (Chrome) | "Was that page served from BFcache?"                                          | F12 → Application → Back/forward cache → "Test back/forward cache".                                                                                       |
| **DevTools — Application → Storage**                     | "What's in the session cookie?" / "Did the cookie expire?"                    | F12 → Application → Storage → Cookies → `<domain>`.                                                                                                       |
| **DevTools — Console**                                   | "What did the page's JS log?"                                                 | F12 → Console.                                                                                                                                            |
| **Reload (`Cmd+R` / `F5`)**                              | "Was this restored from cache vs a real fresh request?"                       | A reload forces a server round-trip. If `back()` shows X but reload shows Y, you have a cache layer involved.                                             |
| **`curl -v <URL>`**                                      | "What does the server actually return on a request from outside the browser?" | Terminal. `-v` for headers, `-I` for HEAD-only.                                                                                                           |
| **PHP source**                                           | "What does the deployed server logic actually do?"                            | `gh api repos/katalon-studio/katalon-demo-cura/contents/<file>.php --jq '.content' \| base64 -d`                                                          |
| **Comparison to `IDENTIFIED_GAPS.md`**                   | "Is this already a documented gap / env artifact?"                            | Read the file. If the symptom matches §A-ENV-1 (rapid-POST flake), §A-ENV-2 (password modal), or a `G-*` / `B-*` entry, the explanation is already there. |

Render this layer as a small section that follows the manual repro:

```markdown
## If you want to confirm a hypothesis

The observation can be ambiguous on first sight. Tools to firm it up:

- **<Suspected cause A>**: <tool> + <one-line how to read the result>.
- **<Suspected cause B>**: <tool> + <one-line how to read the result>.
- **The symptom might match a documented artifact**: see `IDENTIFIED_GAPS.md` §<ref> if it fits.
```

Keep it short. The point is to _unblock_ the user, not to walk them through every diagnostic in the kitchen.

## Layer 3 — cross-browser contrast (only when the finding IS a cross-browser difference)

This layer appears **only** when reproducing in a second browser yields a different observation at a specific step. If both browsers behave
identically, this layer is noise — skip it.

When it applies (BFcache, dispatcher-handler differences, autoplay policies, etc.), structure as a side-by-side or as a "repeat steps 1–N in
<other browser>, observe at step <N>:" callout:

```markdown
## Contrast — same steps in <other browser>

Repeat steps 1–6 in `<other browser>`. At step 5, instead of `<observation in browser A>`, you see `<observation in browser B>`. That divergence _is_
the finding.

The pair `<browser A>: X, <browser B>: Y` is what to record — not "one of them is wrong". Both are real browser behaviours; the test suite's job is to
surface the divergence (per `CLAUDE.md` → "A cross-browser behavioural difference is a finding").
```

If the contrast layer is genuinely the _whole_ finding (one browser exposes something, the other doesn't), the manual recipe pair is the artifact —
there isn't necessarily a layer-1 / layer-3 split, just two side-by-side reproductions.

## Procedure

### 1. State the finding in one sentence

"After logout, pressing Back in Chrome leaves the History page on screen; in Firefox the same press redirects to the homepage." Or: "On the
appointment form, pressing Enter in the date field does not submit." Or: "An appointment for yesterday is silently accepted by CURA and confirmed."

### 2. Pick the layers

By the table above. Most findings need layer 1; flake / state symptoms add layer 2; cross-browser findings add layer 3.

### 3. Write layer 1 — the repro

Number the steps. URLs verbatim. Observations specific. Demo credentials referenced by constant name (`DEMO_USERNAME`, `DEMO_PASSWORD`).

### 4. (If needed) write layer 2 — confirmation

Pick the two or three confirmation tools most relevant to the suspected cause. Don't list every DevTools panel ever — list the one(s) that will
resolve the ambiguity for _this_ finding.

### 5. (If applicable) write layer 3 — contrast

Repeat steps in the other browser; mark the divergence at the exact step it appears.

### 6. Surface — produce the guide

Render the assembled guide. Default: print in chat. If the user wants to keep it:

- **As a recipe in `IDENTIFIED_GAPS.md`** — append a "Manual reproduction" / "Confirmation recipe" block to the relevant entry. (The project already
  does this for §B-BROWSER-1; mirror the shape.)
- **As a one-off in `<gitignored>/repro_<topic>.md`** — for findings still under investigation, not yet ready for the gaps file.

Use this exact template for the assembled guide:

```markdown
# Manual reproduction — <one-sentence finding>

## Setup

- Browser: `<browser, version>` (note: not the OS unless OS-specific).
- Target: <https://katalon-demo-cura.herokuapp.com/> (the deployed app; not the github source).
- Credentials: `DEMO_USERNAME` / `DEMO_PASSWORD` from `src/constants/credentials.py` (public).

## Manual reproduction

<numbered steps — layer 1>

## If you want to confirm a hypothesis (optional)

<layer 2, only if needed>

## Contrast — same steps in <other browser> (optional)

<layer 3, only if the finding is a cross-browser difference>

## Cross-references

- Documented in: `IDENTIFIED_GAPS.md` §<ref>, `CURA_FRD.md` §<ref> (if applicable).
- Related Selenium test: `<test name>` in `<scenario file>`.
- Related probe: `<probe file>` (deleted; see `write-a-probe`).
```

### 7. Stop. The user runs the repro.

The skill produces the document. Running it is on the user — this is a human-driven artifact by design.

## Worked example (from this session)

Finding: _"After logout, pressing Back in Chrome leaves the History page on screen; in Firefox the same press redirects to the homepage. The
difference is Chrome's back-forward cache restoring a `no-store` page."_

Layer 1 — manual repro (Chrome):

1. Open Chrome, navigate to `https://katalon-demo-cura.herokuapp.com/profile.php#login`.
2. Log in as `DEMO_USERNAME` / `DEMO_PASSWORD`. Land on the "Make Appointment" page.
3. Navigate to `https://katalon-demo-cura.herokuapp.com/history.php`. See "History" heading + "No appointment." + "Go to Homepage" button.
4. Open the hamburger menu (top-right `☰`) → click `Logout`. Land on the marketing homepage.
5. Press the browser Back button (◀ or `Cmd+[`).
6. **Observe** — Chrome shows the History page again (URL = `…/history.php`).

Layer 2 — hypothesis confirmation:

- **Is this BFcache?** Press `Cmd+R` (reload). If reload redirects to `/`, the server is doing its job — `back()` served a cached snapshot. (BFcache.)
- **DevTools proof**: F12 → Application → Back/forward cache → "Test back/forward cache". Chrome reports the page as eligible / served from BFcache.

Layer 3 — contrast (Firefox):

- Repeat steps 1–5 in Firefox. At step 6, Firefox re-requests `/history.php`, the server sees no session, returns a 302 to `/`. You land on the
  marketing homepage, no stale History view.

Cross-references: documented in `IDENTIFIED_GAPS.md` §B-BROWSER-1, FRD §9.11.

That's the artifact. It went into the GAPS entry and stayed there.

## When to run this skill

- The user asks: "write up the manual repro for X", "how do I check this by hand?", "give me a recipe to share with the team".
- After a Selenium probe (`write-a-probe`) confirms a finding — produce the human-runnable companion so the finding is verifiable without running
  Python.
- After `review-suite-stability` surfaces a flake the user wants to chase manually.
- When adding an entry to `IDENTIFIED_GAPS.md` — the recipe block lives there for future readers.

## What this skill does NOT do

- It does not run the reproduction itself — it produces the document; the user runs it.
- It does not perform the empirical verification (that's `empiricism` and the Layer 2 confirmation tools).
- It does not write a Selenium test (that's a separate authoring step; see `empiricism` + the scenario file structure rules).
- It does not include attack-shape inputs in any step — see `CLAUDE.md` → "Security testing is functional and static — never active". A manual recipe
  is fine for functional behaviour and security-relevant findings observable through the normal UI; it never asks the user to type a SQL injection
  string into a form.
