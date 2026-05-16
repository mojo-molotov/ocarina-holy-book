---
name: review-compartmentalisation-leaks
description:
  "**Static review for compartmentalisation leaks** — places in the codebase where a literal that *should* live in its canonical module appears inline
  elsewhere, breaking the project's separation-of-concerns policy. The project keeps URLs in `src/constants/urls.py`, credentials in
  `src/constants/credentials.py`, transient-error classifications in `src/constants/transient_errors.py`, selectors inside POMs only, etc. A leak is
  when a URL string appears hard-coded in a scenario, a selector tuple is written outside a POM, a magic timeout sits inline in a connector, a
  credential value is typed directly rather than imported. The skill greps each canonical module's *expected residents* and flags every off-residence
  occurrence, classified by leak kind (URL leak, selector leak, credential leak, magic-number leak, configuration leak, cross-layer leak) with the
  recommended canonical home and the move shape. Use whenever the user asks to audit compartmentalisation, find leaks, check that constants stay
  constant, audit URL/selector residence, or review the codebase's separation-of-concerns hygiene."
---

# Review compartmentalisation leaks — literals that escaped their module

A static-review skill. The project enforces a compartmentalisation policy: certain kinds of literal _belong_ in a specific module and nowhere else.
URLs live in `src/constants/urls.py`. Credentials live in `src/constants/credentials.py`. Transient-error classifications live in
`src/constants/transient_errors.py`. Selectors live inside POMs only, never in scenarios or connectors. Magic numbers (timeouts, retry counts) sit in
named constants, not inline.

The policy supports the _"Use the constant"_ rule in `CLAUDE.md` and the _"Datasets are authoring decisions"_ rule by keeping authoring data under
deliberate control. A leak — a URL string typed inline in a scenario when it should be `LOGIN_URL`, a selector tuple instantiated in a connector
rather than read from its POM — is a silent erosion of that control.

The skill grep-walks each canonical module's residents and surfaces every off-residence occurrence. Static review only; never edits.

## The seven leak kinds

For each kind: what the canonical home is, what the leak looks like, how to spot it.

### 1. URL leak

Any URL or path string used **as a navigation target** outside `src/constants/urls.py`.

- **Canonical home**: `src/constants/urls.py` (or its sibling files if the project splits by domain).
- **What counts as a leak**: a string literal passed to `driver.get(...)`, used as the source of truth for a navigation, or assigned to a URL-shaped
  variable, anywhere outside `urls.py`.
- **What does NOT count (legitimate inside POMs)**:
  - Selector strings that happen to contain a path: `(By.CSS_SELECTOR, "#sidebar-wrapper a[href='history.php#history']")`. The path is a CSS attribute
    value, not a navigation target.
  - URL-substring assertions in waits: `ec.url_contains("appointment.php")`, `lambda d: "history.php" not in d.current_url`. The POM observes the URL;
    it doesn't define it.
  - Docstring / comment mentions of paths for explanation purposes.
  - Log messages that name a page: `log_error("Navigation to appointment.php failed")`. The path is part of the message, not a navigation directive.
- **Detection** (raw grep; expect false positives, then filter against the "does NOT count" list):
  ```bash
  grep -rn "http://\|https://" src --include="*.py" | grep -v constants/urls.py
  grep -rn "\.php" src --include="*.py" | grep -v constants/urls.py
  ```
  The first grep is high-signal (almost any `http(s)://` outside `urls.py` is a leak). The second is noisy on this kind of codebase and needs the
  filter above.
- **Recommended move** (for real leaks): introduce a named constant in `urls.py`, import it at the leak site.

### 2. Credential leak

Any username / password / token literal outside `src/constants/credentials.py`.

- **Canonical home**: `src/constants/credentials.py` (`DEMO_USERNAME`, `DEMO_PASSWORD`).
- **Leak shape**: a string literal equal to `"John Doe"`, `"ThisIsNotAPassword"`, or any other credential constant's value, anywhere else.
- **Detection**:
  ```bash
  grep -rn "John Doe\|ThisIsNotAPassword" src .github --include="*.py" --include="*.yml" | grep -v constants/credentials.py
  ```
- **Recommended move**: import `DEMO_USERNAME` / `DEMO_PASSWORD` and reference them. The project already corrected this for `valid_login.py` (see
  recent commit); the leak-check stays as a regression guard.
- **Note**: the credentials are intentionally public for this demo SUT — the discipline is about _referencing the constant_, not about secrecy.

### 3. Selector leak (POM internals leaking to scenarios / connectors)

Any Selenium locator tuple (`(By.X, "...")`) outside a POM file.

- **Canonical home**: `src/pages/**/*.py` only. Selectors are POM-internal.
- **Leak shape**: `(By.ID, "...")`, `(By.CSS_SELECTOR, "...")`, `(By.XPATH, "...")` outside `src/pages/`. Also: raw selector strings (`"#submit"`,
  `"//button[contains(...)]"`) appearing in scenario / connector files where they're being passed to `find_element` directly.
- **Detection**:
  ```bash
  grep -rn "By\.ID\|By\.CSS_SELECTOR\|By\.XPATH\|By\.NAME\|By\.CLASS_NAME" src --include="*.py" | grep -v "src/pages/"
  grep -rn "find_element\|find_elements" src --include="*.py" | grep -v "src/pages/"
  ```
- **Recommended move**: introduce a POM method exposing the operation (`page.click_submit()`), call that from the scenario / connector. If the
  selector lives in a component, route through the component (e.g. `Sidebar`).

### 4. Magic-number leak (timeouts, retry counts, limits)

Numeric literals representing timeouts, retry budgets, polling intervals, or limits — outside a named constant.

- **Canonical home**: `src/constants/` (the appropriate file by domain — `transient_errors.py` for retry, a new module if needed).
- **Leak shape**: `time.sleep(2)`, `WebDriverWait(driver, 15)`, `range(10)` (when 10 is a retry budget), `if attempts > 3:` inline.
- **Detection**:
  ```bash
  grep -rn "time\.sleep\|WebDriverWait(.*,\s*[0-9]" src --include="*.py" | grep -v constants/
  ```
  Manual inspection needed beyond grep — magic numbers are context-sensitive.
- **Recommended move**: name the constant in `src/constants/` with a comment on its _why_ (matches the project's commenting discipline — only WHY,
  never WHAT).

### 5. Configuration leak (env-derived values inline)

Values that should be read from configuration (env var, CI matrix, config file) appearing inline.

- **Canonical home**: `src/constants/` for compile-time defaults; env vars for run-time overrides (e.g. `WAIT_TIMEOUT` in
  `.github/workflows/e2e.yml`).
- **Leak shape**: a fixed wait timeout in a connector that should be `WAIT_TIMEOUT`. A browser name hard-coded in a scenario that should come from the
  matrix.
- **Detection**: case-by-case. Look at any place a CI matrix value is implied but a literal is used.
- **Recommended move**: factor through the configuration layer (env var read at module load), import the resolved value.

### 6. Cross-layer leak (scenarios reaching past POM public surface)

A scenario file touching **private** POM members — single-underscore attributes / methods (`_btn_login`, `_wait_for_form`, `_internal_helper`).

- **Canonical home**: scenarios call connectors and POM **public** methods; POMs encapsulate selectors and internal state under `_*` names. Public
  imports (`from src.pages.login import LoginPage`) are normal and expected — scenarios need POM classes for construction and type hints. The leak is
  _only_ when a scenario reaches **past the public surface** into a private member.
- **What counts as a leak**: `page._btn_login`, `page._wait_for_x()`, `Sidebar._internal_helper(...)` — any access of an `_`-prefixed POM attribute /
  method from outside a POM file.
- **What does NOT count**: importing a POM class, constructing it, calling its public methods.
- **Detection**:
  ```bash
  # Scenarios accessing private POM members (the real leak)
  grep -rnE "[A-Za-z_]+\._[a-z][a-zA-Z_]*" src/tests --include="*.py" \
    | grep -v "^[^:]*:[^:]*:[[:space:]]*#" \
    | grep -v "self\._" \
    | grep -vE ":[[:space:]]*(from|import) "
  ```
  The exclusions remove comments, `self._*` (legitimate inside a POM), and `from ... import ...` lines (which can match directory names like
  `_fragments/`). Refine manually beyond that: filter out matches on objects that aren't POMs (e.g. `logger._foo`, `driver._foo` — those are out of
  this skill's scope).
- **Recommended move**: introduce a POM public method (or a connector method) that exposes the operation properly; rename the private member if it
  should have been public; if the access is intentional and rare, document it inline with a one-line _why_.
- **Note**: the earlier formulation of this rule ("scenarios shouldn't import from `src/pages`") is too aggressive for projects where scenarios
  legitimately construct POMs. The boundary that matters is _public vs private surface_, not _import vs no-import_.

### 7. Domain-string leak (user-facing strings outside their localisation / fixture home)

Strings the SUT renders that the test asserts against, scattered inline rather than centralised.

- **Canonical home**: depends on project shape; commonly `src/constants/messages.py` or per-domain fixture modules.
- **Leak shape**: `"Login failed!"`, `"Make Appointment"`, `"No appointment."` typed inline in multiple scenario files.
- **Detection**:
  ```bash
  # Same string appearing in multiple files — heuristic
  grep -rn "\"[A-Z][a-zA-Z ]\{5,\}\"" src/tests --include="*.py"
  ```
  Inspect occurrences for repeat / divergence.
- **Recommended move**: extract to a named constant if used in >1 place, or if it represents a contract with the SUT's UI.
- **Note**: not every UI string needs extraction — single-use strings are fine inline. The leak is when the _same_ string appears multiple times.

## Procedure

### Step 1 — Inventory the canonical modules

```bash
ls src/constants/
```

For the current project: `credentials.py`, `urls.py`, `transient_errors.py`, plus `__init__.py`. Note each module's purpose. If a leak kind has no
canonical module yet (e.g. messages), surface that as part of the audit — the missing module is itself a finding.

### Step 2 — Walk the seven leak kinds

For each kind:

- Run the detection grep.
- Filter false positives (comments, docstrings, test data that's _intentionally_ literal).
- Capture each true positive as `(file:line, leak kind, current value, recommended move)`.

### Step 3 — Classify each finding

- **Hard leak** — clearly violates the policy (URL hard-coded in a scenario when the constant exists). Recommend move.
- **Soft leak** — borderline (a magic number that arguably is self-explanatory). Surface for user judgment.
- **Missing-module leak** — leak exists because no canonical module exists yet (e.g. UI messages with no `messages.py`). Recommend creating the module
  before moving.
- **Intentional inline** — false positive (e.g. a test deliberately asserting against a literal value to detect drift). Don't propose a move.

### Step 4 — Cross-check against CLAUDE.md rules

For each finding, cite the supporting rule:

- "Use the constant" → URL / credential / magic-number leaks.
- "Datasets are authoring decisions" → magic-number / domain-string leaks (because they shape what tests observe).
- Existing POM / connector / scenario layering convention → cross-layer leaks.

### Step 5 — Surface the audit

```markdown
# Compartmentalisation-leak audit — <project-name> (<date>)

## Canonical modules

- `src/constants/urls.py` — URL constants.
- `src/constants/credentials.py` — credential constants.
- `src/constants/transient_errors.py` — retry classification.
- (Missing: `src/constants/messages.py` for UI messages? — surface if leaks suggest the need.)

## Findings

### URL leaks

- `src/<file>.py:<line>` — `"<literal URL>"` inline. Should reference `urls.<NAME>` (or introduce a new constant). Severity: hard.
- ...

### Credential leaks

- ...

### Selector leaks

- ...

### Magic-number leaks

- ...

### Configuration leaks

- ...

### Cross-layer leaks

- ...

### Domain-string leaks

- ...

## Missing canonical modules (recommended)

- `src/constants/messages.py` — UI strings asserted against in tests (`"Login failed!"`, `"No appointment."`, etc.). Currently scattered. Suggested
  shape: one constant per asserted message, named by REQ-id when possible.

## False positives reviewed

- (Optional — items the grep flagged that turned out to be intentional inline. Useful to show the audit walked them.)

## Cross-references

- `CLAUDE.md` → "Use the constant" rule (anchors URL / credential / magic-number findings).
- `CLAUDE.md` → "Datasets are authoring decisions" rule (anchors domain-string / magic-number findings).
- Sister review skills: `review-type-ignore`, `review-comment-drift`, `review-intent-collisions`.

## Recommended next motions

- For each hard leak: prepare an edit moving the literal into its canonical module and importing it at the call site. Batch by kind (all URL leaks in
  one PR, all selector leaks in another) so the diff stays focused.
- For each missing-module finding: discuss with the user before creating — adding a module is a project-shape decision.
- For each soft leak: user judgment.

## Verdict

<one-line: N hard leaks, K soft leaks, J missing modules surfaced, nothing material>.
```

Print the audit. Do not edit any file.

### Step 6 — Stop. The user decides.

Each finding resolves as:

- **Move** — the user (or a follow-up edit motion) factors the literal into its canonical module.
- **Keep inline** — the user judges the leak is acceptable (e.g. truly one-off).
- **Create module** — the user creates the missing canonical module, then moves leaks into it.
- **Defer** — record for the next refactor pass.

## Hard rules

- **Static review only.** The skill surfaces; the user applies. Moving literals is authoring data — per the project's discipline, that's a user
  decision.
- **Batch fixes by leak kind in one PR.** A "URL hygiene" PR is easier to review than a mixed-bag refactor. The skill recommends the batching shape;
  the user implements.
- **Don't recommend creating a canonical module without surfacing first.** A new constants module is a project-shape decision (the project's memory
  notes: scope is the project only — confirm with the user before adding structure).
- **Distinguish hard, soft, missing-module, intentional inline.** Not every literal is a leak. The classification matters.
- **Cite the CLAUDE.md rule that justifies each finding.** Otherwise the audit becomes opinion.
- **Don't propose moving literals that exist for behavioural detection.** A test that intentionally asserts against a hardcoded `"Login failed!"`
  string to detect SUT drift is doing its job — moving it to a constant might hide future drift behind an import.
- **False positives are part of the audit.** Surfacing what was _checked and dismissed_ (briefly) shows the audit was thorough.

## When to run this skill

- Periodically as part of code-hygiene reviews.
- After a refactor that changed module structure — leaks often follow movement of code.
- Before a release — clean leaks make the changelog cleaner too.
- When adding a new kind of literal (a new credential, a new URL, a new domain string) — verify the new canonical home holds.
- Onboarding — a contributor's first PR is the highest-risk leak vector.

## What this skill does NOT do

- It does not edit any file. Static review surfaces; the user applies.
- It does not create new canonical modules unilaterally. Recommends; user decides.
- It does not audit non-leak refactor opportunities (rename, restructure, extract). Use other review skills for those concerns.
- It does not check semantic correctness — a URL constant pointing at the wrong URL is not a leak (it's a bug; outside this skill's lens).
- It does not run tests after recommending a move. Verifying the move didn't break anything is the user's motion.
- It does not include attack-shape literals anywhere. Per `CLAUDE.md` → "Security testing is functional and static — never active".
