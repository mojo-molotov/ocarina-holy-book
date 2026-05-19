---
sticky: 1
description: Если мы не верим в свободу выражения мнений для людей, которых мы презираем, мы вообще в неё не верим.

date: 2026-04-30

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Расширяемость

## ValidationChain

Используется в POMs, `validate` позволяет выражать инварианты как цепи. Выполнение **отложено**: `.execute()` должен быть вызван явно.

Результат выставляет `is_valid`, `errors` и `validated_values`. Это инертно по умолчанию. `.raise_if_invalid()` выбрасывает исключение, если
необходимо.

```python
validate(checkbox.is_selected(), name="checkbox_is_selected").assert_that(
  is_truthy, msg="Couldn't select the OTP checkbox."
).execute().raise_if_invalid()
```

### Объединение инвариантов

Несколько утверждений на одном значении:

```python
validate(unsafe_min_date, name="cached_min_date")
.assert_that(is_str)
.assert_that(is_iso_utc_date_string).execute().raise_if_invalid()
```

### Объединение валидаций

Несколько валидаций на разных значениях:

```python
chain_validations(
    validate(unsafe_username, name="cached_username").assert_that(is_str),
    validate(unsafe_min_date, name="cached_min_date")
    .assert_that(is_str)
    .assert_that(is_iso_utc_date_string),
).execute().raise_if_invalid()
```

### Переиспользуемые инварианты

Чтобы учесть повторяющуюся валидацию, создайте _Invariant Validator_:

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

Соглашение: `FrameworkInvariantValidator.create` для технических инвариантов, `BusinessInvariantValidator.create` для бизнес-инвариантов.

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

### Тип безопасности

Проверка типов ловит утверждения, несовместимые с типом значения:

```python
validate("lol", name="n").assert_that(is_positive)

# error: Argument 1 to "assert_that" of "ValidationStartBlock" has incompatible type "Callable[[float], None]"; expected "Callable[[str], None]"
```

## Success и Failure

`.success` и `.failure` каждый принимают _effect_ для выполнения.  
[Канонический пример](https://github.com/mojo-molotov/ocarina-example) реализует несколько обработчиков: простой логинг ошибок, логинг ошибок с
текущим URL, логинг успеха и логинг успеха со скриншотом (+ URL).

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

Другие обработчики стоит рассмотреть:

- **`create_log_error_with_retry_hint`**: сигнализирует о _transient error_ и, следовательно, о возможности flakiness,
- **`create_log_error_and_send_alert`**: отправляет webhook при неудаче, не загрязняя сам тест,
- **`create_log_success_and_record_timing`**: захватывает временную метку завершения для измерения фактической длительности шага (комбинируется с
  `on_run_effect` из `create_act`),
- И т. д.

Также стоит рассмотреть _combinator_.

## Плагины

`bootstrap` позволяет плагинам после выполнения запускаться на основе результатов цикла тестирования. Например, `generate_docx_proof` проходит по
дереву логов и генерирует один документ Word (тестовое доказательство) для каждого тестового случая, встраивая скриншоты и преобразуя временные метки
UTC в локальное время.

Идея: плагины переставляют артефакты, произведённые на ходу, в другую форму. Плагин, генерирующий отчет веб-панели, будет естественным выбором,
например.

## Расширяемая грамматика

Грамматика тестовых сценариев построена на одном типе: `ChainRunner[T]`. Сценарий — это `list[ChainRunner]`, выполняемый последовательно, с коротким
замыканием на первом отказе. `drive_page` — это просто тонкая обёртка вокруг `chain_actions`, которая строит `ChainRunner`. Любая функция,
возвращающая `ChainRunner`, подключается без касания фреймворка.

`match_page` был добавлен, чтобы обрабатывать страницы с переменным состоянием (опциональные баннеры, A/B тесты, страницы обслуживания...): он
оценивает условия по порядку и запускает первую совпадающую ветвь.

Другой пример был бы **`skip_if`**: намеренный пропуск части сценария на условии без отказа (вернёт нейтральный `Ok`), полезный для опциональных
шагов, зависящих от окружения или данных.

**Единственный контракт расширения: верните `ChainRunner`.**

<llm-exclude>

---

![Вы читаете Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Для писателя, как и для художника, стиль — это не вопрос техники, а вопрос видения."</p>

<p align="right" class="inspiring-quote-author">― Марсель Пруст</p>

</llm-exclude>
