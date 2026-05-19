---
name: setup-environment
description: Stand up the local dev environment for an Ocarina suite — Python venv, runtime + dev tooling (ruff, mypy, pre-commit), the project's driver adapter choice (Selenium by default; any other Ocarina-supported adapter, or a locally-built one if the user wants something Ocarina doesn't ship), per-machine driver paths, and the quality-check loop run before every commit. Use this skill on first checkout, after a `pip install`-breaking change (new dependency, Python upgrade, lockfile rewrite), when switching driver adapter (Selenium ↔ Playwright ↔ a custom one), or whenever `pre-commit` / `ruff` / `mypy` invocations need to be re-grounded. The skill is intentionally narrow: it does not modify the CI workflow, the `.pre-commit-config.yaml` hook list, or the project's lint configuration — it only walks the steps to make the existing configuration runnable locally and aligned with CI. Pairs with `CLAUDE.local.md` (per-machine driver paths + adapter choice) and the `--driver-path` flag documented in `CLAUDE.md` → "Running tests".
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

## Step 3 — Install the pre-commit hooks

```bash
pre-commit install --config .pre-commit-config.yaml
```

The hook config is repo-tracked; `pre-commit install` only wires the local `.git/hooks/pre-commit` shim. Re-run it whenever the hook config changes
substantively (new hook IDs, new mirror revs).

## Step 4 — Pick the driver adapter

Ocarina is adapter-shaped: the framework's hard couplings are the test hierarchy (`Test → TestSuite → TestCampaign → TestCycle`), the scenario DSL
(`drive_page` / `act`), and the typed plumbing around them — _how_ it drives the browser is delegated to an adapter. **Selenium is the default and the
worked-examples adapter**; this skill assumes Selenium unless the user says otherwise.

If the user wants a different driver layer (Playwright, an HTTP-only adapter for API-side coverage, a CDP-direct adapter for a use case Selenium can't
serve, a project-internal experimental adapter), resolve in this order:

1. **Ask the user.** _"Selenium, or another adapter? If another — Playwright, an Ocarina-shipped one, or a local build?"_ Don't infer from grep
   ambiguities; the adapter is an authoring decision, not a default to assume.
2. **Check Ocarina's shipped adapters.** List the adapter modules in the installed Ocarina (or its clone — path tracked in `CLAUDE.local.md`):
   ```bash
   ls .venv/lib/python3.*/site-packages/ocarina/adapters/ 2>/dev/null || ls <ocarina-clone>/src/ocarina/adapters/
   ```
   If the requested adapter is there, use it. Pin the install if it's an extras group (`pip install .[playwright]` or similar — read
   `pyproject.toml`'s optional-dependencies first).
3. **Build it locally if Ocarina doesn't ship it.** Place the adapter under `src/lib/ext/ocarina/adapters/<name>/`, mirroring the shape of the
   Selenium adapter (`src/lib/ext/ocarina/adapters/selenium/` in this project, or `ocarina/adapters/selenium/` upstream — read either as the
   reference). The local adapter follows the same philosophy as the Selenium one:
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
   adapters before one is canonised). See Step 5 for the template addition.

A non-Selenium adapter changes what driver paths matter (Playwright manages its own browsers — no chromedriver path; an HTTP adapter has no driver
binary at all). Step 5 only asks for paths the chosen adapter actually consumes.

## Step 5 — Per-machine config (`CLAUDE.local.md`)

`CLAUDE.local.md` is gitignored and stores per-machine paths and adapter choice. If it's missing, create it from the template in `CLAUDE.md` →
"CLAUDE.local.md template" — and **ask for the paths, don't guess**. Things to fill in:

- **Adapter** — the choice from Step 4. Record as a section, e.g.:

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
- **Ocarina source repo clones** — Ocarina + the example repos. Used for framework-internals lookup (the Holy Book is authoritative for the documented
  surface; clones are authoritative for everything else). The clone is also the canonical reference when building a local adapter (Step 4).

## Step 6 — Quality checks (run before every commit)

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

## Step 7 — Smoke-check the runner

A 30-second confidence check that the venv is wired correctly and the adapter resolves. Run a single test (or the smoke campaign) before declaring
setup done. Flags depend on the adapter chosen in Step 4 — Selenium needs `--driver-path` / `--browser`, Playwright takes a `--browser-channel`
instead, an HTTP adapter takes neither. Read the chosen adapter's `<Name>CliStoreSingleton` for the exact keys.

Selenium example (the worked-example adapter):

```bash
python -u src/main.py \
  --driver-path <path/to/chromedriver> \
  --browser chrome \
  --workers 2 \
  --wait-timeout 10 \
  --logger terminal \
  --only <one-smoke-test-id>
```

`python src/main.py`, not `python -m src.main` — `src/` is the source root directory, not a package; script form correctly puts `src/` on
`sys.path[0]` so intra-suite imports read `from constants.urls import …`, never `from src.constants.urls import …`. CI uses the script form; match it.

If this exits clean, setup is done. If it doesn't, the failure mode tells you which step regressed (unknown CLI key → Step 4 adapter mismatch; driver
path → Step 5; import error → Step 2; lint pre-commit complaint → Step 6).

## When to re-run this skill

- First clone on a new machine.
- Python minor-version bump (`.venv` is version-locked; rebuild it).
- A dependency change in `pyproject.toml` that `pip install .` would resolve differently.
- A `.pre-commit-config.yaml` change introducing new hook IDs or mirror revs.
- After a driver upgrade (new Chrome major → new chromedriver → new path in `CLAUDE.local.md`).
- **When switching driver adapter** (Selenium ↔ another Ocarina-shipped one ↔ a local build). The adapter line in `CLAUDE.local.md`, the CLI flags in
  the smoke check, and any optional-dependency install all need to follow.

## What this skill does NOT do

- It does not modify `pyproject.toml`, `.pre-commit-config.yaml`, or `ruff` / `mypy` configuration — those are project-level decisions, not setup
  steps.
- It does not change CI workflow files. The CI gate is the canonical reference; local setup mirrors it, never the other way round.
- It does not install browsers or download drivers. Driver acquisition is out of scope (use the browser vendor's distribution channel); this skill
  only wires the path once the binary exists.
- It does not guess driver paths or credentials. `CLAUDE.local.md` is gitignored precisely because per-machine values must be supplied, not inferred.
- It does not pick the adapter for the user. The choice is surfaced (Step 4) and recorded (Step 5); the decision stays with the user, the same as a
  dataset choice (see `CLAUDE.md` → "Datasets are authoring decisions").
- It does not fork Ocarina. A locally-built adapter lives in `src/lib/ext/ocarina/adapters/<name>/` inside the suite — upstreaming it (if ever) is a
  separate motion, not a setup step.
