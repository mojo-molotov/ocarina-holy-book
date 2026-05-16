---
name: review-match-candidates
description:
  Audit Python source for `if/elif/elif` chains that would read better as a `match` statement — while being judicious. `match` is the right tool for
  structural / literal / type-based dispatch on a single expression, not for arbitrary boolean predicates. Use whenever the user asks to review
  `match` usage, find `match` candidates, audit `elif` chains, modernise conditionals, or harden a refactor. Surface candidates with reasoning; never
  auto-rewrite. A skill that says "every elif could be a match" is wrong and produces churn — the value is in distinguishing genuine candidates from
  chains that should stay `if/elif`.
---

# Review — `match` candidates

Audits a Python source tree (or a diff / branch / file list) for `if/elif/elif` chains that would read better as a `match` statement. The discipline:
`match` is for **structural / literal / type-based dispatch on a single expression**, not for arbitrary boolean predicates. Many `elif` chains should
stay as they are; apply judgment.

Default target: `src/`. For a different target, ask the user.

The audit surfaces candidates only. **It never rewrites code.** A bad `match` rewrite costs the reader more than a clear `if/elif`. The job is to
surface chains where `match` would genuinely improve clarity, and to _not_ surface chains where it wouldn't.

`match` was added in Python 3.10 (assuming the project targets 3.10+, it is available everywhere).

## When `match` is the right tool — and when it isn't

|                         | `match` is right                                                                                   | keep `if/elif`                                                                                                |
| ----------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Discriminator**       | one expression, evaluated once; all branches dispatch on it                                        | different expressions / different variables per branch                                                        |
| **Cases**               | literal / type / structural patterns (`case "a"`, `case Foo(...)`, `case (x, y)`, `case {"k": v}`) | arbitrary boolean predicates (`x > 5 and y < 10`), comparisons, side-conditions                               |
| **Closed set?**         | the discriminator's domain is finite (a `Literal`, enum, sum type, fixed string set)               | open-ended / runtime-determined                                                                               |
| **Chain length**        | 3 or more meaningful branches                                                                      | 2 branches — `if/else` reads fine                                                                             |
| **Naturalness**         | the data shape _invites_ destructuring (tuples, mappings, dataclasses)                             | data is already addressed by `obj.attr` with simple equality — `match` would add bracket noise without payoff |
| **`isinstance` chains** | type-based dispatch is the canonical `match` case (`case A(...)` / `case B(...)`) — High           | not applicable                                                                                                |

## Procedure

### 1. Locate `if/elif` chains in the target

A first-pass grep:

```bash
grep -nE "^\s*elif " <target>/**/*.py
```

This finds every `elif`. The chain _length_ is what matters: count consecutive `elif`s under one `if` to find chains of 3+ branches. For precision
when there's any doubt, walk the AST (find `ast.If` whose `orelse` is another `ast.If`, recursively, ≥ 3 levels). The grep first pass is usually
enough.

For a diff/branch audit, restrict to changed Python files first:

```bash
git diff --name-only main..HEAD -- '*.py'
```

### 2. Classify each chain

| Tier      | When                                                                                                                                                                                                 |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **High**  | All branches dispatch on the _same_ expression via literal / type / structural patterns AND the chain is 3+ branches AND the discriminator's domain is closed/finite. `isinstance` chains land here. |
| **Maybe** | Same-expression dispatch, 3+ branches, but with side-conditions in some branches, or open-ended domain. Worth a second look; rewrite cost may exceed gain.                                           |
| **No**    | Different expressions per branch, arbitrary predicates, ≤ 2 branches, or any anti-indicator from the table above. **Do not surface.** A skill that flags every `elif` produces churn.                |

### 3. Diagnose each High / Maybe candidate

Work out _what the `match` rewrite would look like_ before recommending. Write the proposed `match` block concretely in the report so the user can
judge it on its merits — not on a hand-wave. If the rewrite would require restructuring beyond a direct translation (introducing a dataclass to enable
a class pattern, splitting an `and` clause across cases), note that — sometimes the indirection isn't worth it.

### 4. Report

Use this exact template:

````markdown
# `match` candidates — <target>

## High — `match` would be a clear win

- <path>:<line> — <one-line summary: discriminator + N branches>

  Current:

  ```python
  <slice of the if/elif chain>
  ```
````

Proposed:

```python
<the match rewrite>
```

Why: <one or two sentences — same expression, structural/literal/type pattern, closed domain, etc.>

## Maybe — judgment call

- <same shape; explicitly note the trade-off>

## Summary

- High: N | Maybe: N
- Verdict: <N candidates worth reviewing | nothing worth changing>

````

Print the report; do not write it to a file unless the user asks.

### 5. Stop. The user decides.

Do not edit. Do not propose a sweeping refactor commit. Hand the report over. A High candidate may still be left as-is for style reasons; the audit's job is visibility, not enforcement.

## Examples

### Good `match` candidate (would surface as **High**)

```python
# current
if platform.system() == "Windows":
    return _create_win_store()
elif platform.system() == "Darwin":
    return _create_macos_store()
elif platform.system() == "Linux":
    return _create_linux_store()
else:
    raise RuntimeError(f"Unsupported platform: {platform.system()}")
````

Same expression evaluated multiple times; three literal-string branches; closed domain. The `match` rewrite reads better and evaluates the expression
once:

```python
match platform.system():
    case "Windows":
        return _create_win_store()
    case "Darwin":
        return _create_macos_store()
    case "Linux":
        return _create_linux_store()
    case other:
        msg = f"Unsupported platform: {other}"
        raise RuntimeError(msg)
```

### `isinstance` chain (would surface as **High**)

```python
# current
if isinstance(result, Success):
    handle_success(result.value)
elif isinstance(result, Failure):
    handle_failure(result.error)
elif isinstance(result, Pending):
    handle_pending(result.eta)
```

Type-based dispatch is the canonical `match` case:

```python
match result:
    case Success(value=v):
        handle_success(v)
    case Failure(error=e):
        handle_failure(e)
    case Pending(eta=t):
        handle_pending(t)
```

### NOT a candidate (must **not** surface)

```python
# keep this as is
if cb.is_selected():
    return self
elif cb.is_enabled():
    cb.click()
    return self
else:
    raise RuntimeError("checkbox disabled")
```

Different methods per branch; not a single expression dispatched on. A `match` rewrite would force an artificial discriminator and obscure the intent.

### Borderline (would surface as **Maybe**, with the trade-off called out)

```python
if browser == "chrome":
    options = ChromeOptions(); ...
elif browser == "firefox":
    options = FirefoxOptions(); ...
```

Only two branches — `if/else` is fine. Surface only if a third meaningful branch lands (`edge`/`safari`) and tips it into `match` territory.

## When to run this skill

- The user asks: "any chains that should be a `match`?", "review `elif` usage", "find `match` candidates", "modernise conditionals".
- A PR adds a new `elif` to an existing chain (it may be the third branch that finally tips it into `match` territory).
- A refactor or release-hardening pass.

You may run it without prompting if you spot a long fresh `if/elif/elif/elif` chain in a diff you're reviewing.

## What this skill does NOT do

- It does not rewrite source files.
- It does not flag every `elif` — that produces churn. Surface only chains where `match` is a genuine improvement.
- It does not enforce style preferences over readability. If the user reviews a High candidate and prefers `if/elif`, that is the right call; the
  audit only made the option visible.
