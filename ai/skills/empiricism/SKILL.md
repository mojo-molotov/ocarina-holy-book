---
name: empiricism
description: Authoring discipline for **new** tests — before writing any assertion, verify empirically what the SUT actually does (read the source when available, probe the live page, inspect rendered HTML, capture cookies/headers), and only then write the test against the observed behaviour. The shorthand: *"Fair point — I'm assuming. Let me verify empirically."* This skill walks you through that loop. It is for **adding new tests**, never for "fixing" intentionally-failing ones — gap tests and documented cross-browser reds are red **by design** and stay red until the SUT changes. Use whenever the user asks to add a test, write a scenario, cover a new flow, harden coverage, or capture a behaviour the suite doesn't yet exercise. Pairs with `write-a-probe` — empiricism is the *discipline* (verify before you encode a test); the probe is one *instrument* it reaches for when the question needs live runtime state (rendered HTML, a redirect chain, network traffic), distinct from this skill, which is the authoring loop itself. Verify; do not theorise.
---

# Empiricism — author new tests by evidence, not by assumption

A short discipline applied at one moment: **just before writing the first assertion in a new scenario**. The rule: every load-bearing claim the test
makes about the SUT must come from _empirical_ observation — not from what you think the SUT does, not from a generic web framework intuition, not
from a comment that says _"the SUT does X"_ without a source citation.

This skill walks you through the loop:

1. State the proposition the new test will assert.
2. Enumerate every load-bearing assumption the proposition rests on.
3. Pick a verification path per assumption (probe / source / live HTML / network).
4. Run the verifications. Record the empirical answer.
5. Write the test against the verified answer — and only then.

It complements `CLAUDE.md` → "Verify SUT behaviour — don't theorise" and "Throwaway probes". This skill names the _workflow_; those rules name the
_principles_.

## Critical scope guard — never overwrite intentionally-failing tests

This skill is for **adding new tests**. It does **not** "fix", flip, or rewrite tests that are red by design.

A mature suite carries a small set of intentional reds — tests asserting behaviour the SUT _should_ exhibit but currently doesn't, each one documented
in the gap inventory and (if user-facing) the FRD. As a worked instance, the gap table from <https://github.com/mojo-molotov/ocarina-with-ai-example>
looks like this:

| Test                                                                        | Why it's red                                | Reference                                     |
| --------------------------------------------------------------------------- | ------------------------------------------- | --------------------------------------------- |
| `Appointment - Past date booking accepted`                                  | SUT has no temporal validation              | FRD §9.7                                      |
| `Appointment - Server accepts empty date when client bypass applied`        | SUT has no server-side date validation      | FRD §9.1                                      |
| `Appointments - Duplicate booking (same facility, date, program)`           | SUT has no uniqueness constraint            | FRD §9.6                                      |
| `Appointments - Overlapping appointments (same date, different facilities)` | SUT has no geographic-conflict detection    | FRD §9.6                                      |
| `Journey - History ordered most-recent date first`                          | SUT renders history in submission order     | FRD §9.8 / §4.4                               |
| `Logout - Back-button does not restore authenticated history view`          | Chrome BFcache restores the `no-store` page | FRD §9.11 / `IDENTIFIED_GAPS.md` §B-BROWSER-1 |
| `Logout - Session holds under back-forward stress (3 cycles)`               | Same; held under back/forward churn         | FRD §9.11 / `IDENTIFIED_GAPS.md` §B-BROWSER-1 |

Your project will have its own; the schema is `Test name | Why it's red | Reference into gap inventory or FRD`.

If a new test you're about to author would assert the **opposite** of any documented red (i.e. assert that the SUT _does_ enforce the constraint, or
that the browser _does not_ restore from BFcache), **stop**. That's not a new test — it's an attempt to flip a gap-test to green. The gap stays red
until the SUT is fixed; the suite is _intentionally_ not silent about the defect.

Same rule for the empirical loop itself: if a probe surprises you with _"actually the SUT does enforce X now"_, the right response is **not** "flip
the gap test to green." The right response is:

- Re-run the probe carefully (deterministic? on a clean browser? on the deployed app, not a fork?).
- If genuinely fixed, that's a finding worth a separate change: update the FRD's known-bugs section, update the gap inventory, then — and only then —
  rewrite the relevant gap test as a regression-guard happy path.

In other words: a probe surprises you → it goes through the docs, not into the test, until the user signs off.

## The loop

### Step 1 — State the proposition

In one sentence, what will the test assert? Example: _"On a fresh login, the history page shows an empty-state message and a button to return to the
homepage."_

If the proposition is fuzzy ("the history page works"), refine it until it points at one concrete observable.

### Step 2 — Enumerate the load-bearing assumptions

For the example: the assertion rests on at least four assumptions about the SUT's behaviour:

1. After a fresh login, navigating to `/history` lands you on a page (no redirect).
2. That page contains a `#history` landmark element.
3. The page displays specific text indicating empty state (what text exactly?).
4. The page displays a button (with what label? what `href`?).

Each one is a _claim about the SUT_. None of them is OK to write into an assertion until verified.

### Step 3 — Pick a verification path per assumption

The tools in order of cost (lowest first):

| Verification                       | When                                                                                                                                                                              | How                                                                                                                                                                                                        |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Read the SUT source                | The claim is about a server-side decision (which template renders, whether a redirect fires, what query the page runs), and the source is accessible (open source, or you own it) | Backend-stack dependent. Examples: `gh api repos/<org>/<repo>/contents/<file>.php --jq '.content' \| base64 -d`; clone a Node/Java/Go/Ruby repo; read the OpenAPI / GraphQL schema for a closed-source SUT |
| Read the rendered HTML             | The claim is about what the page shows (text, button label, structure)                                                                                                            | A throwaway probe (gitignored, ~30 lines) that logs in, navigates, prints `driver.page_source` or a `querySelector(...)` slice. Or just inspect the live page in a real browser.                           |
| Capture cookies / response headers | The claim is about session, caching, redirects                                                                                                                                    | A `curl -v` or a `requests.get` probe — but **read-only**, no payload crafting (see `CLAUDE.md` → "Security testing is functional and static").                                                            |
| Drive the exact flow               | The claim is about an interaction's _outcome_ on the exact target                                                                                                                 | A throwaway probe that drives the exact locator on the exact screen with the exact wait condition and the exact action (`CLAUDE.md` → "Evidence is local — re-derive for every new question").             |

If two tools give the same answer, prefer the cheaper one. If they disagree (e.g. source says one thing, live HTML another — common when a deployment
drifts from the source), the live observation wins.

### Step 4 — Run the verifications, record the answer

For each assumption, write down the empirical answer in the scenario file's docstring or call-site comment — _not_ in a separate note that drifts.
Future readers should see: _"the rendered button literally says `Go to Homepage`, confirmed against the deployed app on YYYY-MM-DD."_

If a verification fails to give a definite answer (intermittent, environment-dependent), **don't write the test yet** — flag the indeterminacy. A test
built on "probably" produces flake or false confidence.

### Step 5 — Write the test against the verified answer

Now and only now: the assertions, the locators, the expected text. Each assertion traces back to a verified observation.

Verify after writing: open the test, walk every assertion, ask _"where did this string / locator / expected URL come from?"_ If the answer is _"I
assumed"_, go back to Step 2 for that one.

## Worked example

From a real session in <https://github.com/mojo-molotov/ocarina-with-ai-example>: the user wanted a test for the empty-state history page. The
empirical loop:

1. **Proposition**: _"On a fresh login with no bookings, the history page shows an empty-state message and a 'Go to Homepage' button."_
2. **Assumptions**:
   - History page reachable on fresh login (no redirect).
   - Contains a `#history` landmark.
   - Empty-state text exists with specific wording.
   - Button exists with specific label and href.
3. **Verification path** — start with the SUT source for the redirect logic (cheapest, here it was PHP), then a quick live HTML inspection for the
   rendered strings.
4. **Empirical answers** — `history.php` → renders `views/page_history.php` directly when `is_user_logged_in()` (no redirect for the authenticated
   case); the empty-state text is literally `No appointment.`; the button text is `Go to Homepage` and routes via `./`.
5. **Test written against the verified answers** — `verify_history_is_empty()` matches `//*[normalize-space()='No appointment.']`;
   `click_go_to_homepage()` matches `//a[normalize-space()='Go to Homepage']`. No assumption invented; each locator traces to an observation.

The earlier draft of the test had _guessed_ the text would be `Your history is empty.` That was the assumption-driven path. The probe corrected it;
the empirical text went into the locator.

## When to run this skill

- The user asks: "add a test for X", "write a scenario for Y", "cover this flow", "what's missing here?" (combined with `extend-coverage` for the gap,
  then `empiricism` for the authoring).
- A new POM or new page lands and needs scenarios.
- A new SUT flow / mechanism comes into scope.
- You catch yourself about to write `assert text == "..."` and you didn't open the page to read it.

## When NOT to apply this loop

- An **existing intentionally-failing test surprises you by passing.** Don't rewrite to "match the new reality" without going through the docs first
  (gap inventory, FRD's known-bugs section). The pass may be a transport flake or environment artifact making the gap test pass for the wrong reason;
  verify the _cause_ before changing the test.
- An **existing test fails** for a reason you don't yet understand. The empirical loop applies to _new_ tests, not to making old failures go away.
  Investigate the failure first (probe, log, screenshot) — only then decide whether to amend the test, file a bug, or update the docs.
- A scenario you're **only refactoring** (renaming, moving, screenshot rule application, dispatcher introduction). Refactors preserve the contract;
  the empirical loop is about _new_ contracts.

## What this skill does NOT do

- It does not flip intentionally-failing tests to green — gap tests and BFcache reds are red by design and stay red.
- It does not write the test for you — it walks the loop and produces verified facts; you (or a downstream authoring step) write the test.
- It does not run a full suite. It runs probes, reads source, inspects HTML. Suite execution is a separate motion.
- It does not surface probes themselves into the repo — probes live in a gitignored directory and are deleted once the finding lands in a test,
  comment, or gap-inventory entry (per `CLAUDE.md` → "Throwaway probes").
- It does not propose security/attack-shape inputs. See `CLAUDE.md` → "Security testing is functional and static — never active."
