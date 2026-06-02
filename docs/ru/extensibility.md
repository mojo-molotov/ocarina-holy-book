---
sticky: 1
description: Если мы не верим в свободу слова для тех, кого презираем, значит, не верим в неё вовсе.

date: 2026-04-30

head:
  - - meta
    - property: og:image
      content: https://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Расширяемость

## ValidationChain

`validate` применим внутри POM-ов и позволяет описывать инварианты в виде цепочек. Выполнение **отложенное**: `.execute()` нужно вызвать явно.

Результат предоставляет `is_valid`, `errors` и `validated_values`. По умолчанию он инертен. При необходимости исключение выбросит
`.raise_if_invalid()`.

```python
validate(checkbox.is_selected(), name="checkbox_is_selected").assert_that(
  is_truthy, msg="Couldn't select the OTP checkbox."
).execute().raise_if_invalid()
```

### Сцепление инвариантов

Несколько утверждений для одного значения:

```python
validate(unsafe_min_date, name="cached_min_date")
.assert_that(is_str)
.assert_that(is_iso_utc_date_string).execute().raise_if_invalid()
```

### Сцепление валидаций

Несколько валидаций для разных значений:

```python
chain_validations(
    validate(unsafe_username, name="cached_username").assert_that(is_str),
    validate(unsafe_min_date, name="cached_min_date")
    .assert_that(is_str)
    .assert_that(is_iso_utc_date_string),
).execute().raise_if_invalid()
```

### Переиспользуемые инварианты

Чтобы вынести повторяющуюся валидацию, создайте _Invariant Validator_:

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

Соглашение: `FrameworkInvariantValidator.create` — для технических инвариантов, `BusinessInvariantValidator.create` — для бизнес-инвариантов.

### Пользовательские утверждения

Без аргумента:

```python
def is_str(value: Any) -> None:
    if not isinstance(value, str):
        msg = "Expected value to be string."
        raise InvariantViolationError(msg)
```

С аргументом:

```python
def is_equal_to(cmp: Any) -> Predicate[Any]:
    def unwrapped(value: Any) -> None:
        if value != cmp:
            msg = f"{value} is not equal to {cmp}."
            raise InvariantViolationError(msg)

    return unwrapped
```

### Безопасность типов

Тайпчекер ловит утверждения, несовместимые с типом значения:

```python
validate("lol", name="n").assert_that(is_positive)

# error: Argument 1 to "assert_that" of "ValidationStartBlock" has incompatible type "Callable[[float], None]"; expected "Callable[[str], None]"
```

## Success и Failure

`.success` и `.failure` — каждый принимает _effect_, который нужно выполнить.  
[Канонический пример](https://github.com/mojo-molotov/ocarina-example) реализует несколько обработчиков: простое логирование ошибок, логирование
ошибок с текущим URL, логирование успеха и логирование успеха со скриншотом (+ URL).

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

Стоит подумать и о других обработчиках:

- **`create_log_error_with_retry_hint`**: сигнализирует о _transient error_, а значит — о возможной flakiness;
- **`create_log_error_and_send_alert`**: при неудаче отправляет webhook, не засоряя сам тест;
- **`create_log_success_and_record_timing`**: фиксирует метку времени завершения, чтобы измерить фактическую длительность шага (его комбинируют с
  `on_run_effect` из `create_act`);
- и так далее.

Стоит подумать и о _combinator_'е.

## Плагины

`bootstrap` позволяет запускать плагины постобработки, опираясь на результаты тестового цикла. Например, `generate_docx_proof` проходит по дереву
логов и генерирует по одному документу Word (тестовому доказательству) на каждый тестовый случай, встраивая скриншоты и переводя метки времени UTC в
локальное время.

Идея: плагины пересобирают артефакты, накопленные по ходу дела, в другую форму. Например, плагин, генерирующий отчёт в виде веб-дашборда,
напрашивается сам собой.

## Расширяемая грамматика

Грамматика тестовых сценариев построена на одном-единственном типе — `ChainRunner[T]`. Сценарий — это `list[ChainRunner]`, который выполняется
последовательно и обрывается на первом же сбое. `drive_page` — это просто тонкая обёртка вокруг `chain_actions`, которая строит `ChainRunner`. Любая
функция, возвращающая `ChainRunner`, подключается, не затрагивая сам фреймворк.

`match_page` добавили позже — чтобы обрабатывать страницы с переменным состоянием (опциональные баннеры, A/B-тесты, страницы техобслуживания…): он
проверяет условия по порядку и запускает первую подошедшую ветвь.

Ещё один пример — **`skip_if`**: намеренный пропуск части сценария по условию, без сбоя (вернул бы нейтральный `Ok`); пригодится для необязательных
шагов, зависящих от окружения или данных.

**Единственный контракт расширения: верните `ChainRunner`.**

<llm-exclude>

---

![Вы читаете Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До скорой встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Для писателя, как и для художника, стиль — это вопрос не техники, а видения."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Марсель Пруст</p>

</llm-exclude>
