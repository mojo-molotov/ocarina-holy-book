---
sticky: 1
description: И подо льдом поблёскивает река…

date: 2026-04-28

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Первые дзюцу

## Наборы данных

Гонять тест через набор данных в Ocarina просто:

```python
multi_login_dataset: Sequence[MappingProxyType[ImmutableCredentialsKeys, str]] = [
    MappingProxyType(
        {
            "login": "any",
            "password": "figatellu",
        }
    ),
    MappingProxyType(
        {
            "login": "Napoleon",
            "password": "figatellu",
        }
    ),
    MappingProxyType(
        {
            "login": "NoSicilianAllowed",
            "password": "figatellu",
        }
    ),
    MappingProxyType(
        {
            "login": "anonymous",
            "password": "figatellu",
        }
    ),
    MappingProxyType(
        {
            "login": "TheEmpire",
            "password": "figatellu",
        }
    ),
]

def _create_login_scenario(credentials: ImmutableCredentials) -> SeleniumTestScenario:
    """Welcome to functional factories."""

    def _scenario(driver: WebDriver, logger: ILogger):
        dashboard_creds = credentials  # <- [!] Provided by the closure

        on_dashboard_login_page = DashboardLoginPage(driver=driver)
        on_dashboard_welcome_page = DashboardWelcomePage(driver=driver)

        # * ...
        return Scenario(
            test_chain=[
                drive_page(
                    # * ...
                    act(
                        on_dashboard_login_page,
                        login_without_otp_and_with_retries(
                            dashboard_creds,  # <- [!]
                            retries_amount,
                            logger=logger,
                        ),
                    )
                    .failure(
                        just_log_error(
                            "Failed to connect to the dashboard without OTP...",
                        )
                    )
                    .success(
                        just_log_success(
                            f"Connected to the dashboard as {dashboard_creds['login']}!"
                            # ⬆️ [!]
                        )
                    ),
                ),
                drive_page(
                    act(on_dashboard_welcome_page, ...)
                    .failure(...)
                    .success(...)
                ),
            ]
        )

    return _scenario


multi_login_tests = [
    create_selenium_test(
        name=f"Login - {creds['login']}",
        test_scenario=_create_login_scenario(creds),
    )
    for creds in multi_login_dataset
]
```

Достаточно одного [_closure_](<https://en.wikipedia.org/wiki/Closure_(computer_programming)>).  
Обратите внимание: `Scenario` здесь объявляется изнутри. И это логично — вся суть как раз в том, чтобы её инкапсулировать.

Итак, `multi_login_tests` — это _list_ объектов `Test`, который мы _unpack_'аем в `TestSuite`, вот так:

```python
def create_suite(
    *,
    drivers_pool: SeleniumWebDriversPool,
) -> TestSuite:
    return TestSuite(
        name="Login (data-driven PoC)",
        tests=[*multi_login_tests],
        drivers_pool=drivers_pool,
    )
```

## Smoke-тесты

<llm-exclude>

> 📖 Smoke-тест — это быстрая, поверхностная проверка программной системы: она подтверждает, что основные функции работают как надо, прежде чем
> переходить к более глубоким тестам. Цель — пораньше отловить очевидные блокирующие сбои: если всё сразу заволакивает дымом, идти дальше нет смысла.

</llm-exclude>

Чтобы запустить smoke-тесты в начале цикла на Ocarina:

```python
E2E_CYCLE_NAME = "My very first cycle with Ocarina"

def create_e2e_test_cycle(drivers_pool: SeleniumWebDriversPool):
    """e2e test cycle."""
    return TestCycle(
        name=E2E_CYCLE_NAME,
        campaigns=[
            create_my_first_campaign(drivers_pool=drivers_pool),
        ],
        smoke_tests_campaigns=[
            create_my_first_smoke_campaign(drivers_pool=drivers_pool),
            create_my_second_smoke_campaign(drivers_pool=drivers_pool),
        ],
        mode="wait-for-all-smoke-tests",
    )
```

`mode` принимает два значения (по умолчанию: `"fail-fast-on-first-smoke-campaigns-sequence-fail"`):

- `"fail-fast-on-first-smoke-campaigns-sequence-fail"`: как только проваливается одна кампания smoke-тестов, остальные пропускаются.
- `"wait-for-all-smoke-tests"`: все кампании smoke-тестов отрабатывают до конца, даже если какая-то по пути провалилась.

В обоих случаях основные тесты пропускаются, если провалился хоть один smoke-тест.

## Setup и teardown

`Scenario` принимает два опциональных обратных вызова: `setup` и `teardown`.

```python
Scenario(
    setup=seed_test_user,
    test_chain=[
        drive_page(
            act(page, open_page)
                .failure(log_error("Failed to open..."))
                .success(log_success("Opened!")),
        ),
    ],
    teardown=delete_test_user,
)
```

### Жизненный цикл

1. `setup()`: выполняется перед `test_chain`. При сбое `test_chain` пропускается, а `teardown` всё равно выполняется. Если все попытки провалились
   из-за setup, тест помечается как **SKIPPED** (а не **FAILED**);
2. `test_chain`: собственно шаги теста;
3. `teardown()`: выполняется всегда, даже при сбое. Ошибки логируются и игнорируются.

`setup` и `teardown` — это `Effect`.  
Они предназначены для инфраструктурных задач: наполнить базу данных, вызвать API, подчистить состояние…

Если нужна инкапсуляция: _closure_.

## Паттерн Proxy

Один из примеров применения из [канонического примера](https://github.com/mojo-molotov/ocarina-example) — `HumanizedDriver`:

```python
class HumanizedDriver(WebDriver):
    def __init__(
        self, driver: WebDriver, **keyboard_config: Unpack[KeyboardConfig]
    ) -> None:
        object.__init__(self)
        self._driver = driver
        self._config = keyboard_config

    def find_element(
        self,
        by: str | RelativeBy = "id",
        value: str | None = None,
    ) -> _HumanizedWebElement:
        element = self._driver.find_element(by, value)
        return _HumanizedWebElement(element, self._config)

    def find_elements(
        self,
        by: str | RelativeBy = "id",
        value: str | None = None,
    ) -> list[WebElement]:
        elements = self._driver.find_elements(by, value)
        return [_HumanizedWebElement(el, self._config) for el in elements]

    def __getattr__(self, name: str):
        return getattr(self._driver, name)
```

Идея: возвращать _Web Elements_, которые ведут себя иначе при взаимодействиях, похожих на пользовательские. В нашем случае — нажатия клавиш.  
Прозрачно для _type system_, прозрачно для _runtime_.

Что затем позволяет:

```python
create_selenium_test(
    name="Send the form",
    test_scenario=lambda driver, logger: Scenario(
        test_chain=_send__form(
            HumanizedDriver(  # <- [!]
                driver,
                wpm=125,
                typo_rate=0.14,
                hesitation_rate=0.02,
                burst_rate=0.35,
                late_correction_rate=0.6,
            ),
            logger,
        ),
    ),
)
```

Или, с _closure_:

```python
def _scenario(driver: WebDriver, logger: ILogger):
    humanized_driver = HumanizedDriver(  # <- [!]
        driver,
        wpm=125,
        typo_rate=0.14,
        hesitation_rate=0.02,
        burst_rate=0.35,
        late_correction_rate=0.6,
    ),

    on_some_form_page = SomeFormPage(driver=humanized_driver)  # <- [!]
```

Тот же принцип работает и для логгера — например, перенаправляя его в _sink_. Канонически Ocarina этот случай не покрывает.

## Реактивное программирование: НЕТ

Тестовые сценарии Ocarina намеренно статичны.  
Однако веб-приложение динамично, и порой вполне законно перехватить значение на лету и передать его на более поздний шаг.

Ocarina на это не отвечает. Ей это и не нужно.

### Архитектурный ответ

Здесь нам нужен _in-memory cache_.

Мы генерируем ключи прямо перед стартом тестовой цепочки и передаём их в действия POM. Действия пишут и читают по уникальному ключу.  
Сценарий лишь раздаёт их:

```python
# * ...
cache = in_memory_cache_with_30m_ttl
username_key = reserve_free_cache_key(cache)
otp_send_date_key = reserve_free_cache_key(cache)

return [
    drive_page(
        # * ...
        act(
            on_dashboard_login_page,
            start_to_login_with_otp_and_with_retries(
                dashboard_creds,
                retries_amount,
                cache=cache,
                logger=logger,
                username_key=username_key,
                otp_send_date_key=otp_send_date_key,
            ),
        )
        .failure(
            just_log_error(
                "Failed to fill and confirm the login form with OTP...",
            )
        )
        .success(
            just_log_success(
                "Filled and confirmed the login form with OTP!"
            )
        ),
        act(
            on_dashboard_login_page,
            verify_otp_screen,
        )
        .failure(
            just_log_error(
                "Failed to verify the OTP screen...",
            )
        )
        .success(just_log_success("Verified the OTP screen!")),
        act(
            on_dashboard_login_page,
            type_otp_with_retries(
                retries_amount,
                cache=cache,
                logger=logger,
                username_key=username_key,
                otp_send_date_key=otp_send_date_key,
            ),
        )
        .failure(
            just_log_error(
                "Failed to confirm the OTP code...",
            )
        )
        .success(just_log_success("Confirmed the OTP code!")),
    ),
    # * ...
]
```

## Вызовы API и блокировки

API и блокировки нужно обрабатывать в POM-ах.

> ⚠️ Ocarina не поддерживает `async`/`await` и никогда не будет.

**Вызовы API**: достаточно синхронного `requests`.  
**Блокировки**: `threading.Lock`, если в каждый момент работает только один процесс; иначе хватит распределённых блокировок Redis
(`redis.StrictRedis` + `redis.lock`).

## Профиль браузера

Некоторые случаи требуют передать профиль через `--profile-path`:

- **Аутентификация на прокси**,
- **Предустановленные расширения**,
- **Локальные настройки** (язык, часовой пояс, сертификаты…),
- и так далее.

<llm-exclude>

---

![Вы читаете Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До скорой встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Мутную воду лучше всего очищать, оставив её в покое."</p>

<p align="right" class="inspiring-quote-author">― Алан Уотс</p>

</llm-exclude>
