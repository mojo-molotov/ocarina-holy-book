---
name: setup-environment
description:
  Stand up the local dev environment for an Ocarina suite — Python venv, runtime + dev tooling (ruff, mypy, pre-commit), the project's driver adapter
  choice (Ocarina ships **two** adapters — Selenium and Playwright, the latter since v1.1.3 — or a locally-built one if the user wants something
  Ocarina doesn't ship; the choice is the user's, neither is a silent default), per-machine driver paths, the quality-check loop run before every
  commit, the Ocarina skill battery (the Holy Book's `ai/skills/`) copied into Claude Code's skills directory so the workflows are invokable, and the
  suite's **adapter-resolved `CLAUDE.md`** assembled from the Holy Book (the framework-neutral core concatenated with the chosen adapter's appendix —
  `CLAUDE.selenium.md` or `CLAUDE.playwright.md` — as a regenerable artifact). Use this skill on first checkout, after a `pip install`-breaking change
  (new dependency, Python upgrade, lockfile rewrite), when switching driver adapter (Selenium ↔ Playwright ↔ a custom one — the generated `CLAUDE.md`
  is re-assembled with the other appendix), whenever `pre-commit` / `ruff` / `mypy` invocations need to be re-grounded, or after the Holy Book's
  `ai/skills/` or `ai/CLAUDE*.md` changes (the Claude Code skill copy and the suite's generated `CLAUDE.md` must be refreshed). The skill stays narrow
  on CI — it does not modify the CI workflow — but it does verify (and create if missing) the project's strict `ruff` (in `pyproject.toml`), `mypy`
  (in `mypy.ini`), and pre-commit (`.pre-commit-config.yaml`) configuration, so a fresh project gets the `select = ["ALL"]` + strict-mypy +
  ruff/mypy-pre-commit baseline of the worked examples instead of the tools' lenient defaults. Use it also when that strict config has drifted or been
  reset. Pairs with `CLAUDE.local.md` (per-machine driver paths + adapter choice) and the `--driver-path` flag documented in `CLAUDE.md` → "Running
  tests".
---

# Setup environment — local venv, tooling, driver paths, quality checks

A short, repeatable procedure to make a freshly-cloned Ocarina suite runnable, lintable, and type-clean on this machine. The steps below are the
canonical shape; defer to the project's `pyproject.toml` / `.pre-commit-config.yaml` if it pins different versions or extra dependencies.

## Step 1 — Python venv

```bash
python -m venv .venv
source .venv/bin/activate
```

Python version: match what `pyproject.toml` declares (or CI uses). If `python` resolves to an older version, use `python3.X -m venv .venv` with the
right minor.

## Step 2 — Install runtime + dev tooling

```bash
pip install . ruff mypy mypy-extensions typing-extensions pre-commit
```

`pip install .` reads `pyproject.toml` and pulls Ocarina + suite dependencies. The dev tools (`ruff`, `mypy`, `pre-commit`) are usually not in the
runtime dependency set — install them explicitly.

If the project pins additional dev tooling in an optional-dependencies group (`pip install .[dev]`), use that form instead.

## Step 3 — Pre-commit hooks (config + install)

Two parts: the repo-tracked `.pre-commit-config.yaml` (the hook set), then `pre-commit install` (the local `.git/hooks/pre-commit` shim). Verify the
config matches `ocarina-with-ai-example`; create it if missing. If one exists but differs (extra hooks, a different rev, a `local` mypy hook wired
differently), surface the diff and **ask before changing it** — same rule as Step 8's config.

This is the config — it runs the same three tools as the quality loop (Step 9), so a commit is gated on exactly what CI checks:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12 # author's choice — see note below
    hooks:
      - id: ruff-format
        files: ^src/
      - id: ruff-check
        files: ^src/
        args: [--fix]

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: mypy src/
        language: system
        types: [python]
        pass_filenames: false
        files: ^src/
```

Notes:

- **`rev` is the author's call** — pin to a fixed version, track latest, or match the installed ruff; don't impose `v0.15.12` (that's just what
  `ocarina-with-ai-example` happens to pin). Just be aware: if `rev` and the installed ruff diverge, the hook and the local `ruff check src/` can
  disagree (the drift Step 9 warns about). If you create the file fresh, a sensible default is the installed `ruff version`, but leave an existing
  `rev` alone unless the author wants it bumped.
- **mypy is a `local` / `language: system` hook** — it runs the venv's `mypy`, the same binary as Step 9, so the `mypy.ini` from Step 8 is honoured.
  `pass_filenames: false` + `entry: mypy src/` means it always checks the whole `src/` tree, not just staged files (mypy needs the full module graph).

Then wire the local shim:

```bash
pre-commit install --config .pre-commit-config.yaml
```

`pre-commit install` only wires `.git/hooks/pre-commit`; it does not validate the config content. Re-run it whenever the hook config changes
substantively (new hook IDs, new mirror revs).

## Step 4 — Install the Ocarina skill battery into Claude Code

The ~40 workflow skills ship with **the Holy Book** (`mojo-molotov/ocarina-holy-book`), under its `ai/skills/` directory (catalogued in
`ai/skills/README.md` there). They are **not** vendored into the test suite — a suite checkout has no `ai/skills/` of its own. So the source is a
local clone of the Holy Book: use the path recorded in `CLAUDE.local.md` (Step 6 lists it among the repo clones), or clone it now if it is missing:

```bash
git clone https://github.com/mojo-molotov/ocarina-holy-book.git <path>
```

Claude Code only discovers skills from its own skills directories — it does not read the Holy Book's `ai/skills/` directly. Copy the battery from the
clone into one of those directories so the workflows are invokable.

**Ask the user which scope they want** — don't assume:

- **Personal** (`~/.claude/skills/`) — the skills are available in every project on this machine. Right for a contributor who wants the Ocarina
  workflows everywhere.
- **Project** (`.claude/skills/`) — scoped to this repo only. Right when the skills should not leak into the contributor's other projects.

Copy every skill directory (`ai/skills/*/` matches only directories, so `README.md` is excluded; the `SKILL.md` check is the belt-and-suspenders):

```bash
HOLY_BOOK="<path to the ocarina-holy-book clone>"   # the path recorded in CLAUDE.local.md

# Pick ONE destination:
DEST="$HOME/.claude/skills"        # personal — all projects on this machine
# DEST=".claude/skills"            # project — this repo only

mkdir -p "$DEST"
for skill in "$HOLY_BOOK"/ai/skills/*/; do
  [ -f "${skill}SKILL.md" ] || continue   # only directories that hold a SKILL.md
  cp -R "$skill" "$DEST/"
done
```

If you chose the **project** scope, add `.claude/skills/` to `.gitignore` — the copy is a per-machine artifact and `ai/skills/` stays the single
tracked source of truth. Committing the copy would duplicate the battery inside its own repo.

This is a **copy**, not a symlink: it snapshots the Holy Book's `ai/skills/` as it is now. When that directory changes (a `git pull` in the Holy Book
clone adds, removes, or edits skills), re-run this step to refresh the copy — see "When to re-run this skill". A copy survives the clone being moved
or deleted; the cost is that a renamed or removed skill leaves a stale directory at `$DEST` to delete by hand.

## Step 5 — Pick the driver adapter

Ocarina is adapter-shaped: the framework's hard couplings are the test hierarchy (`Test → TestSuite → TestCampaign → TestCycle`), the scenario DSL
(`drive_page` / `act`), and the typed plumbing around them — _how_ it drives the browser is delegated to an adapter. **Ocarina ships two adapters:
Selenium and Playwright** (Playwright since v1.1.3). Neither is a silent default — the adapter is an authoring decision, so **ask**. The suite may
already be wired for one (grep for `create_selenium_test` vs `create_playwright_test`, `WebDriverWait` vs `driver.submit`); confirm rather than
assume.

Resolve in this order:

1. **Ask the user.** _"Selenium or Playwright (both ship with Ocarina)? Or a custom/local adapter (HTTP-only for API-side coverage, CDP-direct, a
   project-internal experimental one)?"_ Don't infer from grep ambiguities; confirm the choice.
2. **Check Ocarina's shipped adapters.** Both Selenium and Playwright ship in the box. Confirm against the installed Ocarina (or its clone — path
   tracked in `CLAUDE.local.md`):
   ```bash
   ls .venv/lib/python3.*/site-packages/ocarina/infra/ 2>/dev/null || ls <ocarina-clone>/src/ocarina/infra/
   # expect a selenium/ and a playwright/ directory
   ```
   For **Playwright**, the suite depends on the `playwright` package and needs its browser binaries: after `pip install .`, run `playwright install`
   (or the project's `make playwright-install`) to fetch chromium/firefox/webkit. For **Selenium**, no `playwright install`; you supply a driver
   binary path instead (Step 6). Pin the install if the adapter is gated behind an extras group (`pip install .[playwright]` — read `pyproject.toml`'s
   optional-dependencies first).
3. **Build it locally if Ocarina doesn't ship it.** Place the adapter under `src/lib/ext/ocarina/adapters/<name>/`, mirroring the shape of the
   Selenium or Playwright adapter (`src/lib/ext/ocarina/adapters/<name>/` in this project, or `ocarina/infra/<selenium|playwright>/` upstream — read
   either as the reference). The local adapter follows the same philosophy as the shipped ones:
   - **Typed end-to-end.** Public surface fully annotated; nothing relies on `Any`. `Effect` / `Thunk` / `TestScenario` signatures match the Ocarina
     primitives.
   - **CLI store + driver pool + driver builder.** Same triad shape: a `<Name>CliStoreSingleton`, a `create_<name>_drivers_pool` factory, a
     `<Name>DriverBuilder`. Keyword names match Ocarina's conventions (`workers`, not `max_workers`; see `CLAUDE.md` → "Opinionated CLI keys").
   - **Mixins where Ocarina has them.** If a navigation / title / wait mixin exists on the Selenium side and applies to the new adapter, build the
     equivalent (`<Name>BackAndForwardNavigationMixin`, `<Name>TitleMixin`). Don't re-invent the wheel; mirror the contracts.
   - **No tricks.** The strictness budget (`ruff select = ["ALL"]`, strict mypy, no `# type: ignore` on framework symbols) applies to the local
     adapter as it does to the suite. Suppressions in adapter code are caught by `review-type-ignore` the same way.
   - **No active security paths.** The adapter exposes the user-facing app surface; raw HTTP / DevTools manipulation outside that surface is out of
     scope (per `CLAUDE.md` → "Security testing is functional and static — never active").

   Don't fork Ocarina to add the adapter. Local adapters live in the suite; if it earns its way back into the framework, that is a separate upstream
   contribution, not a setup step.

4. **Record the choice in `CLAUDE.local.md`.** The adapter selection is per-machine information (different contributors may experiment with different
   adapters before one is canonised). See Step 6 for the template addition.

A non-Selenium adapter changes what driver paths matter (Playwright manages its own browsers — no chromedriver path; an HTTP adapter has no driver
binary at all). Step 5 only asks for paths the chosen adapter actually consumes.

## Step 6 — Per-machine config (`CLAUDE.local.md`)

`CLAUDE.local.md` is gitignored and stores per-machine paths and adapter choice. If it's missing, create it from the template in `CLAUDE.md` →
"CLAUDE.local.md template" — and **ask for the paths, don't guess**. Things to fill in:

- **Adapter** — the choice from Step 5. Record as a section, e.g.:

  ```markdown
  ## Driver adapter

  - Adapter: `selenium` (Ocarina-shipped) | `playwright` (Ocarina-shipped) | `<name>` (local, at `src/lib/ext/ocarina/adapters/<name>/`)
  - Reason (one line, if the choice isn't the default Selenium).
  ```

  This is the load-bearing line — every other per-machine path below is conditional on it.

- **Driver paths** — only those the chosen adapter consumes.
  - Selenium → **chromedriver path** (`find ~/ -name chromedriver -type f 2>/dev/null` locates it on Unix-likes); add geckodriver / msedgedriver only
    when the suite is run against those browsers locally.
  - Playwright → no driver path needed; record the Playwright browser channel(s) installed (`chromium` / `firefox` / `webkit`) and the
    `~/Library/Caches/ms-playwright/...` cache directory if non-default.
  - HTTP / API adapter → no driver path; record the SUT base URL override if the local environment uses one.
  - Custom local adapter → whatever paths the adapter's `<Name>CliStoreSingleton` reads.
- **Ocarina source repo clones** — Ocarina, the example repos, and the Holy Book (`ocarina-holy-book` — the docs _and_ the `ai/skills/` battery Step 4
  copies from). Used for framework-internals lookup (the Holy Book is authoritative for the documented surface; the source / example clones are
  authoritative for everything else). A source clone is also the canonical reference when building a local adapter (Step 5).

## Step 7 — Assemble the suite's adapter-resolved `CLAUDE.md`

The Holy Book ships the Claude context as **three files**: `ai/CLAUDE.md` (framework-neutral core) + `ai/CLAUDE.selenium.md` +
`ai/CLAUDE.playwright.md` (the driver-level appendices). A suite only needs the core **plus the one appendix** for the adapter chosen in Step 5. This
step assembles that into the suite's own root `CLAUDE.md` — the file Claude Code auto-loads — so a fresh checkout actually gets the Holy Book's rules
instead of nothing.

It is a **generated artifact, not a hand-edited file.** Regenerate it (re-run this step) whenever the adapter switches or the Holy Book clone updates,
exactly like the skill-battery copy in Step 4 — same copy-not-symlink rationale. Don't hand-edit the generated file; project-specific rules go in a
clearly-marked separate section (see the overwrite note) or in `CLAUDE.local.md`.

Source = the Holy Book clone (path recorded in `CLAUDE.local.md`). Concatenate the core + the chosen appendix into the suite-root `CLAUDE.md`:

```bash
HOLY_BOOK="<path to the ocarina-holy-book clone>"   # the path recorded in CLAUDE.local.md
ADAPTER="selenium"   # or "playwright" — the choice from Step 5

{
  cat "$HOLY_BOOK/ai/CLAUDE.md"
  printf '\n\n---\n\n'
  cat "$HOLY_BOOK/ai/CLAUDE.$ADAPTER.md"
} > ./CLAUDE.md
```

The **other** adapter's appendix is deliberately omitted — the suite is wired on one adapter, and the core's "→ see the adapter appendix" pointers now
resolve to the appended section in the same file. The slim variant needs no merge (it already inlines the adapter-neutral principle with per-adapter
bullets); copy it verbatim if the suite uses it: `cp "$HOLY_BOOK/ai/CLAUDE.slim.md" ./CLAUDE.slim.md`.

**Ask before overwriting.** If the suite already has a `CLAUDE.md` that isn't a clean prior generation — it carries project-specific rules, a
different SUT's facts, or hand edits — don't clobber it. Surface the diff and offer: (a) regenerate the core+appendix and re-apply the
project-specific section on top (keep that section clearly fenced so the next regen preserves it), (b) keep the suite's `CLAUDE.md` and only
append/refresh the adapter appendix section, or (c) leave it untouched. A freshly-cloned suite with **no** `CLAUDE.md`, or one whose `CLAUDE.md` is a
verbatim prior concat, regenerates without asking. Same rule as the strict-config step below: reaching the Holy Book baseline is the goal, silently
overwriting a deliberate local divergence is the one move to avoid.

## Step 8 — Ensure strict lint + type config in `pyproject.toml`

The quality loop (next step) is only as strict as the config it reads. On a fresh project `ruff` and `mypy` fall back to their lenient defaults —
`ruff` runs a small default ruleset, `mypy` checks almost nothing. Verify the strict baseline matches the worked examples (`ocarina-example` /
`ocarina-with-ai-example`); create it if missing. **Ruff lives in `pyproject.toml`; mypy lives in a separate `mypy.ini`** — that split is the example
shape, don't collapse mypy into `[tool.mypy]`.

**Ruff — `pyproject.toml`:**

```toml
[tool.ruff.lint]
select = ["ALL"]
ignore = [
    # "B008",  # NEVER ignore without understanding function-call-in-default-argument
    "ANN002",  # *args annotation
    "ANN003",  # **kwargs annotation
    "ANN201",  # public-function return type
    "ANN202",  # private-function return type (ocarina-with-ai-example only)
    "TRY003",  # long messages in raise
    "C901",    # function too complex
    "D203",    # conflicts with D211
    "D213",    # conflicts with D212
    "COM812",  # conflicts with the ruff formatter
]

[tool.ruff]
exclude = ["**/.venv/**", "**/bin/**", "**/__init__.py", "**/__bypass_linter__"]
```

`select = ["ALL"]` is the load-bearing baseline. The `ignore` list is **project-owned and deliberate** — the `D203`/`D213`/`COM812` entries resolve
real conflicts with the formatter / each other, and the `ANN`/`TRY003`/`C901` entries are the project's chosen relaxations. Don't strip them to "make
it stricter"; they're there on purpose. (`ocarina-with-ai-example` adds `ANN202` to the list — the lists are close but not byte-identical across
projects.) In ruff ≥ 0.2 `select` lives under `[tool.ruff.lint]`; read the existing table before adding a second one — a duplicated `[tool.ruff.lint]`
is a config error.

**mypy — `mypy.ini`** (separate file, not `pyproject.toml`):

```ini
[mypy]
mypy_path = src
python_version = 3.14
strict = true

# * ... Allow missing annotations (type inference is cool)
disallow_incomplete_defs = false

# * ... Allow missing annotations (type inference is cool)
disallow_untyped_defs = false
```

`strict = true` turns on the full strict bundle, then the two `disallow_*_defs = false` lines deliberately walk back the untyped-def checks so type
inference can cover unannotated defs — that pairing **is** the example baseline, not an oversight. Match `python_version` to what the project's
`pyproject.toml` declares (the examples pin `3.14`). `mypy_path = src` is what lets `mypy src/` resolve intra-suite imports without the `src.` prefix.

Resolve in this order:

- **Present and matches the examples** → leave it; the project already owns this decision.
- **Missing** → create `mypy.ini` and the `pyproject.toml` ruff tables above.
- **Present but weaker** (a partial `select`, `strict` absent/`false`, or per-rule `ignore` / `# noqa` blanket that guts the ruleset beyond the
  example list) → surface the diff and **ask the user before tightening**. Reaching the example baseline is the goal, but silently overwriting a
  project's deliberate relaxation is the one move to avoid — show what you'd change and let the user confirm.

After writing, confirm the tools read it: `ruff check src/` should report the broad ruleset and `mypy src/` the strict checks. The only
`pyproject.toml` edit this skill makes is the ruff tables — it does not touch the dependency lists, build config, or versions.

## Step 9 — Quality checks (run before every commit)

```bash
ruff format src/          # format
ruff check src/           # lint (project's chosen ruleset; ALL is the strict default)
mypy src/                 # type check
pre-commit run --all-files --config .pre-commit-config.yaml
```

All four should be clean before committing. The CI gate should run the same checks — if `ruff` or `mypy` complain locally and CI doesn't, or vice
versa, the local environment has drifted (different tool version, missing dependency, stale venv); investigate before pushing.

`pre-commit run --all-files` is the catch-all — it runs every hook against the full tree, not just staged files. Useful after a bulk rename or
refactor where the staged-file view is misleading.

## Step 10 — Smoke-check the runner

A 30-second confidence check that the venv is wired correctly and the adapter resolves. Run a single test (or the smoke campaign) before declaring
setup done. Flags depend on the adapter chosen in Step 5 — Selenium needs `--driver-path` + `--browser chrome|firefox|edge|safari`; Playwright takes
`--browser chromium|firefox|webkit` (no driver path) plus optional `--video-dir` / `--trace-dir`; an HTTP adapter takes neither. Read the chosen
adapter's `<Name>CliStoreSingleton` for the exact keys.

Selenium example:

```bash
python -u src/main.py \
  --driver-path <path/to/chromedriver> \
  --browser chrome \
  --workers 2 \
  --wait-timeout 10 \
  --logger terminal \
  --only <one-smoke-test-id>
```

Playwright example (no driver path; browsers fetched by `playwright install`):

```bash
python -u src/main.py \
  --browser chromium \
  --workers 2 \
  --wait-timeout 10 \
  --logger terminal \
  --only <one-smoke-test-id>
```

`python src/main.py`, not `python -m src.main` — `src/` is the source root directory, not a package; script form correctly puts `src/` on
`sys.path[0]` so intra-suite imports read `from constants.urls import …`, never `from src.constants.urls import …`. CI uses the script form; match it.

If this exits clean, setup is done. If it doesn't, the failure mode tells you which step regressed (unknown CLI key → Step 5 adapter mismatch; driver
path → Step 6; import error → Step 2; lint/type complaint with the wrong strictness → Step 8; lint pre-commit complaint → Step 9).

## When to re-run this skill

- First clone on a new machine.
- Python minor-version bump (`.venv` is version-locked; rebuild it).
- A dependency change in `pyproject.toml` that `pip install .` would resolve differently.
- A `.pre-commit-config.yaml` change introducing new hook IDs or mirror revs.
- The strict `ruff` config (`pyproject.toml`) or `mypy.ini` drifted, was reset, or a new project lacks it (re-run Step 8 alone to re-ground the
  baseline).
- After a driver upgrade (new Chrome major → new chromedriver → new path in `CLAUDE.local.md`).
- After the Holy Book's `ai/skills/` gains, loses, or edits a skill (a `git pull` in the Holy Book clone, an upstream skill update) — the Claude Code
  copy from Step 4 is a snapshot and must be refreshed (re-run Step 4 alone; the rest of the setup is unaffected).
- After the Holy Book's `ai/CLAUDE*.md` changes (a `git pull` adds or edits a rule, in the core or an appendix) — the suite's generated `CLAUDE.md` is
  a snapshot and must be re-assembled (re-run Step 7 alone).
- **When switching driver adapter** (Selenium ↔ Playwright ↔ a local build). The adapter line in `CLAUDE.local.md`, the **generated `CLAUDE.md`**
  (re-run Step 7 — a different appendix gets concatenated), the CLI flags in the smoke check, and any optional-dependency install all need to follow.

## What this skill does NOT do

- The config it touches is the strict lint/type baseline: the `ruff` tables in `pyproject.toml` (Step 8), the `mypy.ini` file (Step 8), and the
  `.pre-commit-config.yaml` hook set (Step 3) — and even there it asks before tightening a config the project deliberately relaxed. It does not touch
  `pyproject.toml`'s dependency lists, build config, or versions.
- It does not change CI workflow files. The CI gate is the canonical reference; local setup mirrors it, never the other way round.
- It does not install browsers or download drivers. Driver acquisition is out of scope (use the browser vendor's distribution channel); this skill
  only wires the path once the binary exists.
- It does not guess driver paths or credentials. `CLAUDE.local.md` is gitignored precisely because per-machine values must be supplied, not inferred.
- It does not pick the adapter for the user. The choice is surfaced (Step 5) and recorded (Step 6); the decision stays with the user, the same as a
  dataset choice (see `CLAUDE.md` → "Datasets are authoring decisions").
- It does not pick the skill-install scope for the user. Step 4 surfaces personal vs project; the decision stays with the user.
- It does not symlink the skill battery or version it. Step 4 copies — the Claude Code copy drifts from `ai/skills/` until re-run. This is deliberate
  (a copy survives the repo being moved or deleted); the cost is the manual refresh noted above.
- It does not edit the Holy Book's `ai/skills/` or `ai/CLAUDE*.md`. Those are the Holy Book's tracked source of truth; this skill only
  copies/assembles them outward — the skill battery into Claude Code's reach (Step 4), the adapter-resolved `CLAUDE.md` into the suite root (Step 7).
- It does not hand-edit the suite's generated `CLAUDE.md`, nor silently overwrite a `CLAUDE.md` that carries project-specific rules. Step 7 generates
  by concatenation (core + chosen appendix) and asks before clobbering a non-generated file; project-specific rules live in a fenced section or
  `CLAUDE.local.md`, never as hand edits to the generated body.
- It does not fork Ocarina. A locally-built adapter lives in `src/lib/ext/ocarina/adapters/<name>/` inside the suite — upstreaming it (if ever) is a
  separate motion, not a setup step.
