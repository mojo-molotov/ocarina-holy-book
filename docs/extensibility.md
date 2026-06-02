---
sticky: 1
description: If we don't believe in freedom of expression for people we despise, we don't believe in it at all.

date: 2026-04-30

head:
  - - meta
    - property: og:image
      content: https://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Extensibility

## ValidationChain

Usable inside POMs, `validate` lets you express invariants as chains. Execution is **deferred**: `.execute()` must be called explicitly.

The result exposes `is_valid`, `errors`, and `validated_values`. It is inert by default. `.raise_if_invalid()` throws the exception if needed.

```python
validate(checkbox.is_selected(), name="checkbox_is_selected").assert_that(
  is_truthy, msg="Couldn't select the OTP checkbox."
).execute().raise_if_invalid()
```

### Chaining invariants

Multiple assertions on the same value:

```python
validate(unsafe_min_date, name="cached_min_date")
.assert_that(is_str)
.assert_that(is_iso_utc_date_string).execute().raise_if_invalid()
```

### Chaining validations

Multiple validations on different values:

```python
chain_validations(
    validate(unsafe_username, name="cached_username").assert_that(is_str),
    validate(unsafe_min_date, name="cached_min_date")
    .assert_that(is_str)
    .assert_that(is_iso_utc_date_string),
).execute().raise_if_invalid()
```

### Reusable invariants

To factor out a recurring validation, create an _Invariant Validator_:

```python
def _workers_amount_chain(
    chain: ValidationStartBlock[int],
    value: int,
) -> ValidationAssertBlock[int]:
    msg = f"Value Error: Number of workers must be at least 1 (got: {value})."
    return chain.assert_that(is_positive, msg=msg).assert_that(is_not_zero, msg=msg)


def validate_workers_amount(
    *, workers_amount: int, name: str
) -> ValidationAssertBlock[int]:
    """Validate that workers amount is at least 1."""
    return FrameworkInvariantValidator.create(
        workers_amount, name, _workers_amount_chain
    )

# * ...
validate_workers_amount(
    workers_amount=max_workers, name="max_workers"
).execute().raise_if_invalid()
```

Convention: `FrameworkInvariantValidator.create` for technical invariants, `BusinessInvariantValidator.create` for business invariants.

### Custom assertions

Without argument:

```python
def is_str(value: Any) -> None:
    if not isinstance(value, str):
        msg = "Expected value to be string."
        raise InvariantViolationError(msg)
```

With argument:

```python
def is_equal_to(cmp: Any) -> Predicate[Any]:
    def unwrapped(value: Any) -> None:
        if value != cmp:
            msg = f"{value} is not equal to {cmp}."
            raise InvariantViolationError(msg)

    return unwrapped
```

### Type safety

The type checker catches assertions incompatible with the value's type:

```python
validate("lol", name="n").assert_that(is_positive)

# error: Argument 1 to "assert_that" of "ValidationStartBlock" has incompatible type "Callable[[float], None]"; expected "Callable[[str], None]"
```

## Success and failure

`.success` and `.failure` each take an _effect_ to execute.  
[The canonical example](https://github.com/mojo-molotov/ocarina-example) implements several handlers: plain error logging, error logging with current
URL, success logging, and success logging with screenshot (+ URL).

```python
def _append_current_url_in_msg(msg: str, driver: WebDriver) -> str:
    try:
        driver_healthcheck(driver)
        extended_msg = f"{msg}\nCurrent URL: {driver.current_url}"
    except DriverDiedError:
        extended_msg = f"{msg}\nThe WebDriver is down, can't provide the current URL."

    return extended_msg


def create_just_log_error(*, logger: ILogger) -> Callable[[str], FailureHandler]:
    return lambda msg: lambda exc: logger.error(msg, exc=exc)


def create_log_error_with_current_url(
    *, logger: ILogger, driver: WebDriver
) -> Callable[[str], FailureHandler]:
    def unwrapped(msg: str) -> FailureHandler:
        def _log_error_with_url_effect(exc: Exception) -> None:
            extended_msg = _append_current_url_in_msg(msg, driver)
            return create_just_log_error(logger=logger)(extended_msg)(exc)

        return _log_error_with_url_effect

    return unwrapped


def create_just_log_success(*, logger: ILogger) -> Callable[[str], SuccHandler]:
    def unwrapped(msg: str) -> SuccHandler:
        def _log_effect() -> None:
            logger.success(msg)

        return _log_effect

    return unwrapped


def create_log_success_and_take_screenshot(
    *, logger: ILogger, driver: WebDriver
) -> Callable[[str], SuccHandler]:
    def unwrapped(msg: str) -> SuccHandler:
        def _log_and_take_screenshot_effect() -> None:
            performed_dependent_effect = create_just_log_success(logger=logger)(msg)()
            take_screenshot(driver=driver, logger=logger, category="SUCCESS")
            return performed_dependent_effect

        return _log_and_take_screenshot_effect

    return unwrapped


def create_log_success_with_current_url_and_take_screenshot(
    *, logger: ILogger, driver: WebDriver
) -> Callable[[str], SuccHandler]:
    def unwrapped(msg: str) -> SuccHandler:
        def _log_success_with_url_and_take_screenshot_effect() -> None:
            return create_log_success_and_take_screenshot(logger=logger, driver=driver)(
                _append_current_url_in_msg(msg, driver)
            )()

        return _log_success_with_url_and_take_screenshot_effect

    return unwrapped
```

Other handlers are worth considering:

- **`create_log_error_with_retry_hint`**: signals a _transient error_ and therefore the possibility of flakiness,
- **`create_log_error_and_send_alert`**: sends a webhook on failure, without polluting the test itself,
- **`create_log_success_and_record_timing`**: captures an end timestamp to measure the actual duration of a step (to be combined with `on_run_effect`
  from `create_act`),
- Etc.

A _combinator_ would also be worth considering.

## Plugins

`bootstrap` allows post-execution plugins to run based on test cycle results. For instance, `generate_docx_proof` walks the log tree and generates one
Word document (test proof) per test case, embedding screenshots and converting UTC timestamps to local time.

The idea: plugins reassemble artifacts produced along the way into a different form. A plugin generating a web dashboard report would be a natural
fit, for example.

## Extensible grammar

The test-scenario grammar is built on a single type: `ChainRunner[T]`. A scenario is a `list[ChainRunner]` executed sequentially, short-circuiting on
the first failure. `drive_page` is just a thin wrapper around `chain_actions`, which builds a `ChainRunner`. Any function returning a `ChainRunner`
plugs in without touching the framework.

`match_page` was added after the fact to handle variable-state pages (optional banners, A/B tests, maintenance pages...): it evaluates conditions in
order and runs the first matching branch.

Another example would be **`skip_if`**: intentionally bypassing a portion of the scenario on a condition without failing (would return a neutral
`Ok`), useful for environment or data-dependent optional steps.

**The only extension contract: return a `ChainRunner`.**

<llm-exclude>

---

![You reading Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Excellent work!<br/>See you soon, Mojo reader.</i></p>

---

<p align="center" class="inspiring-quote">"For the writer as well as for the painter, style is not a question of technique, but of vision."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Marcel Proust</p>

</llm-exclude>
