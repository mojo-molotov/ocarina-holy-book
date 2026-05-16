---
name: setup-environment
description: Stand up the local dev environment for an Ocarina suite — Python venv, runtime + dev tooling (ruff, mypy, pre-commit), per-machine driver paths, and the quality-check loop run before every commit. Use this skill on first checkout, after a `pip install`-breaking change (new dependency, Python upgrade, lockfile rewrite), or whenever `pre-commit` / `ruff` / `mypy` invocations need to be re-grounded. The skill is intentionally narrow: it does not modify the CI workflow, the `.pre-commit-config.yaml` hook list, or the project's lint configuration — it only walks the steps to make the existing configuration runnable locally and aligned with CI. Pairs with `CLAUDE.local.md` (per-machine driver paths) and the `--driver-path` flag documented in `CLAUDE.md` → "Running tests".
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

## Step 4 — Per-machine config (`CLAUDE.local.md`)

`CLAUDE.local.md` is gitignored and stores per-machine paths. If it's missing, create it from the template in `CLAUDE.md` → "CLAUDE.local.md template"
— and **ask for the paths, don't guess**. The two things to fill in:

- **chromedriver path** — `find ~/ -name chromedriver -type f 2>/dev/null` locates it on Unix-likes.
- **Ocarina source repo clones** — Ocarina + the example repos. Used for framework-internals lookup (the Holy Book is authoritative for the documented
  surface; clones are authoritative for everything else).

Driver binaries for browsers other than Chrome (geckodriver for Firefox, msedgedriver for Edge, Safari's built-in driver) are added to
`CLAUDE.local.md` only when the suite is run against those browsers locally.

## Step 5 — Quality checks (run before every commit)

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

## Step 6 — Smoke-check the runner

A 30-second confidence check that the venv is wired correctly and the driver path resolves. Run a single test (or the smoke campaign) before declaring
setup done:

```bash
python -u -m src.main \
  --driver-path <path/to/chromedriver> \
  --browser chrome \
  --workers 2 \
  --wait-timeout 10 \
  --logger terminal \
  --only <one-smoke-test-id>
```

`python -m src.main`, not `python src/main.py` — script form puts `src/` on `sys.path[0]` instead of the project root, so `from src.X import Y` fails.
CI uses the module form; match it.

If this exits clean, setup is done. If it doesn't, the failure mode tells you which step regressed (driver path → Step 4; import error → Step 2; lint
pre-commit complaint → Step 5).

## When to re-run this skill

- First clone on a new machine.
- Python minor-version bump (`.venv` is version-locked; rebuild it).
- A dependency change in `pyproject.toml` that `pip install .` would resolve differently.
- A `.pre-commit-config.yaml` change introducing new hook IDs or mirror revs.
- After a driver upgrade (new Chrome major → new chromedriver → new path in `CLAUDE.local.md`).

## What this skill does NOT do

- It does not modify `pyproject.toml`, `.pre-commit-config.yaml`, or `ruff` / `mypy` configuration — those are project-level decisions, not setup
  steps.
- It does not change CI workflow files. The CI gate is the canonical reference; local setup mirrors it, never the other way round.
- It does not install browsers or download drivers. Driver acquisition is out of scope (use the browser vendor's distribution channel); this skill
  only wires the path once the binary exists.
- It does not guess driver paths or credentials. `CLAUDE.local.md` is gitignored precisely because per-machine values must be supplied, not inferred.
