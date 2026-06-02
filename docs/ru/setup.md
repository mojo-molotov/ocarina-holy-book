---
sticky: 1
description: Дело не в пункте назначения, а в самом пути.

date: 2026-04-26

head:
  - - meta
    - property: og:image
      content: https://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Первые шаги

## Отказ от ответственности

> **Примечание:** эта книга призвана помочь вам освоиться с проектом `ocarina-example` — он остаётся **источником истины**, к которому следует
> обращаться в любой ситуации.

> ⚠️ _The Ocarina Holy Book_ — это НЕ «plug-and-play» и никогда им не будет. Чтобы пользоваться Ocarina, нужна достаточная зрелость. Поэтому мы
> остановимся только на том, что и правда может оказаться непростым.

Эта страница объясняет _путь_. А дальше понадобится практика.  
[📖 Возьмите за образец канонический пример.](https://github.com/mojo-molotov/ocarina-example)  
[📖 Также доступен с адаптером Playwright.](https://github.com/mojo-molotov/ocarina-with-playwright-example)

## 1. Настройка проекта

Создайте новый проект Python, затем установите необходимые зависимости:

```bash
pip install selenium
pip install ocarina
```

Затем создайте структуру папок.

## 2. Адаптеры

Ocarina построена вокруг системы адаптеров, которые пишет сам пользователь. Они позволяют настроить фреймворк под ограничения и соглашения конкретного
проекта.

Основные адаптеры, которые нужно создать:

- `act` _(требуется)_
- `test_campaign` _(требуется)_
- `test_suite` _(требуется)_
- `env_getters` _(опционально)_
- `match_page` _(опционально)_

### 2.1 EnvGetters

`EnvGetters` в Ocarina централизует и типизирует доступ к переменным окружения. Он делится на две категории:

- **Creds**: пары «логин/пароль», представленные неизменяемыми словарями.
- **Values**: отдельные значения (строки).

```python
type _CredsKeys = Literal["dashboard"]
type _ValuesKeys = Literal["igor_xxx_key", "xxxxx_url"]


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv()


_DEFAULT_EFFECTS = (_load_env,)


class _EnvGetters(EnvGetters[_CredsKeys, _ValuesKeys]):
    def __init__(self, *, effects: Effects) -> None:
        for effect in effects:
            effect()

        super().__init__(
            credentials={
                "dashboard": MappingProxyType(
                    {
                        "login": os.environ["DASH_USERNAME"],
                        "password": os.environ["DASH_PASSWORD"],
                    }
                ),
            },
            values={
                "igor_xxx_key": os.environ["IGOR_XXX_KEY"],
                "xxxxx_url": os.environ["XXXXX_URL"],
            },
        )


def create_env_getters(*, effects: Effects | None = None) -> _EnvGetters:
    """Create a fresh EnvGetter instance."""
    if effects is None:
        effects = _DEFAULT_EFFECTS
    return _EnvGetters(effects=effects)
```

Когда адаптер готов, получение значения или учётных данных выглядит так:

```python
xxxxx_url = create_env_getters().get_value("xxxxx_url")
dashboard_creds = create_env_getters().get_credentials("dashboard")
print(xxxxx_url)
print(dashboard_creds["login"])
print(dashboard_creds["password"])
```

> **Примечание:** допустимые ключи задаются двумя типами: `EnvGetters[_CredsKeys, _ValuesKeys]`. Если нужен только `.get_value()`, достаточно
> типизировать `_CredsKeys` как `Never`. И наоборот: `_ValuesKeys` следует типизировать как `Never`, если нужен только `.get_credentials()`.

После этого наши акцессоры строго типизированы. Например:

```python
xxxxx_url = create_env_getters().get_value("x")

# error: Argument 1 to "get_value" of "EnvGetters" has incompatible type "Literal['x']"; expected "Literal['igor_xxx_key', 'xxxxx_url']"
```

### 2.2 Act

В Ocarina `act` — это глагол, которым выражают каждый отдельный шаг тестового сценария. Его реализацию намеренно оставили на усмотрение пользователя —
по причинам, о которых речь пойдёт дальше в этой книге (_hooks_).

Его минимальная форма выглядит так:

```python
def act(pom: TPOM, action: Callable[[TPOM], TPOM]) -> ActionStart[TPOM]:
    """Act on a page."""

    return create_act(
        pom,
        action,
    )
```

### 2.3 TestCampaign

Адаптер `TestCampaign` намеренно минималистичен. Единственное, что Ocarina не может вывести сама, — это **количество рабочих потоков**, то есть
сколько браузеров запускать параллельно в рамках кампании. А поскольку этот параметр можно передать и напрямую через CLI, достаточно совсем небольшого
адаптера:

```python
@final
class TestCampaign(OriginalTestCampaign[WebDriver]):
    """TestCampaign adapter."""

    def __init__(
        self,
        *,
        name: str,
        suites: Sequence[TestSuite[WebDriver]],
        max_workers: int | None = None,
        saturate_workers: bool | None = None,
    ) -> None:
        """Initialize the campaign."""
        if max_workers is None:
            max_workers = get_max_workers()

        super().__init__(
            name=name,
            suites=suites,
            max_workers=max_workers,
            saturate_workers=saturate_workers,
        )
```

> Тип `WebDriver` (Selenium или другой) подставляется здесь: `OriginalTestCampaign[WebDriver]`.  
> И здесь: `suites: Sequence[TestSuite[WebDriver]]`

> ✅ Разумеется, сюда вставляйте ВАШ собственный `TestSuite`, а не встроенный в Ocarina.

### 2.4 TestSuite

Это адаптер, который важнее всего понять. `TestSuite` из коробки предоставляет множество параметров. Задача нашего адаптера — построить вокруг него
**фасад**: одни значения раз и навсегда зашиты в код, другие — опционально, с разумными значениями по умолчанию. _Сужение_.

Аналогично:

```python
@final
class TestSuite(OriginalTestSuite[WebDriver]):
    """TestSuite adapter."""

    def __init__(
        self,
        *,
        name: str,
        tests: Sequence[Test[WebDriver]],
        drivers_pool: SeleniumWebDriversPool,
        create_logger: Thunk[ILogger] | None = None,
        copy_indicator: str = "+",
        put_space_after_copy_indicator: bool = False,
        autoscreen_on_fail: bool = True,
        saturate_workers: bool | None = None,
    ) -> None:
        """Initialize the TestSuite."""
        if create_logger is None:

            def _create_logger():
                return create_matching_logger(get_logger_mode())

            create_logger = _create_logger

        super().__init__(
            name=name,
            tests=tests,
            only_ids=get_only(),
            exclude_ids=get_exclude(),
            max_retries_per_test=8,
            create_logger=create_logger,
            drivers_pool=drivers_pool,
            copy_indicator=copy_indicator,
            put_space_after_copy_indicator=put_space_after_copy_indicator,
            autoscreen_on_fail=autoscreen_on_fail,
            take_screenshot=_take_screenshot_on_fail,
            transient_errors=transient_errors,
            saturate_workers=saturate_workers,
        )
```

> Тип `WebDriver` (Selenium или другой) подставляется здесь: `OriginalTestSuite[WebDriver]`.  
> А также здесь: `tests: Sequence[Test[WebDriver]]`  
> И здесь: `drivers_pool: SeleniumWebDriversPool`

#### Временные ошибки

Концепция `transient_errors` играет в `TestSuite` центральную роль.  
Такие ошибки считаются **шумом**: если тест упал из-за исключения, перечисленного в `transient_errors`, он автоматически перезапускается.  
Максимальное число попыток задаёт `max_retries_per_test`.

Этот механизм делает прогон тестов устойчивым к _flakiness_. Тесты, которые перезапускаются часто, хорошо заметны в логах — и это позволяет тем, кто
сопровождает проект, находить и устранять источники нестабильности: будь то неправильное использование Selenium, неподконтрольные условия среды или
другие внешние факторы.

#### Only IDs и exclude IDs

Эти два параметра позволяют выполнять тесты выборочно.  
Это фильтры по ID.

> ⚠️ **Обязательно включите их в этот адаптер — иначе эти флаги CLI не будут обрабатываться.**

### 2.5 MatchPage

`match_page` — это оператор Ocarina, созданный для работы со страницами с недетерминированным рендерингом: cookie-баннеры, антибот-проверки, A/B-тесты
и т. д.

Его логика проста: **любое выброшенное исключение трактуется как несовпадение и потому поглощается `match_page`**. Впрочем, часть исключений можно
вывести из-под этого механизма — так, чтобы они нормально распространялись вверх по потоку выполнения.

Ради согласованности `transient_errors`, как правило, должны попадать именно в эту категорию: им положено распространяться, а не тихо проглатываться.

Адаптер создаётся так:

```python
match_page = create_match_page(raised_exceptions=transient_errors)
```

## 3. Пишем первый POM

Паттерн POM (_Page Object Model_) — давно устоявшийся стандарт, и заново определять его мы здесь не станем.

Вот как создать первый POM на Ocarina:

```python
@final
class Homepage(SeleniumTitleMixin, POMBase):
    """My homepage."""

    def __init__(self, *, driver: WebDriver, url: str = HOMEPAGE_URL) -> None:
        """Initialize homepage POM."""
        self._driver = driver
        self._URL = url

    def open(self) -> Homepage:
        """Open the page."""
        self._driver.get(self._URL)
        return self

    def verify(self, *, timeout: float | None = None) -> Homepage:
        """Verify function."""
        try:
            if timeout is None:
                timeout = get_timeout()

            WebDriverWait(self._driver, timeout).until(ec.title_is("Welcome to my homepage"))

            WebDriverWait(self._driver, timeout).until(
                ec.text_to_be_present_in_element(
                    (By.TAG_NAME, "h1"),
                    "My homepage",
                )
            )
        except TimeoutException as exc:
            raise PageVerificationError from exc

        return self
```

Несколько моментов стоит разобрать подробнее.

### 3.1 SeleniumTitleMixin

Любой объект, унаследованный от `POMBase`, обязан реализовать метод `get_current_title`. `SeleniumTitleMixin` даёт эту реализацию прозрачно — вручную
писать её не нужно.

Но этим его роль не исчерпывается: он ещё и задаёт атрибуту `_driver` тип `WebDriver` (Selenium), делая его **несовместимым с любым другим типом**.
Попытка присвоить неподходящее значение сразу же вызовет ошибку типизации:

```python
self._driver = "lol"

# error: Incompatible types in assignment (expression has type "str", variable has type "WebDriver")
```

Тем самым `SeleniumTitleMixin` ещё и работает как **страж типа**. Аналогичные миксины можно создать и для других технологий браузерной автоматизации.

### 3.2 Возврат `self`

Каждый метод-действие возвращает `self`. Это осознанное архитектурное решение Ocarina, которого следует придерживаться неукоснительно: оно позволяет
сцеплять вызовы методов в цепочки и плавно компоновать сценарии.

## 4. Пишем соединители

Соединители — это тонкая, но важная прослойка ради читаемости сценариев. Они оборачивают вызовы методов POM в функции с понятными, явными именами:

```python
def open_homepage(p: Homepage) -> Homepage:
    """Open my homepage."""
    return p.open()


def verify_homepage(p: Homepage) -> Homepage:
    """Verify we are on my homepage."""
    return p.verify()
```

Их также можно компоновать напрямую:

```python
def open_then_verify_homepage(p: Homepage) -> Homepage:
    """Open my homepage, then verify it."""
    return p.open().verify()
```

## 5. Пишем первый тестовый сценарий

Все строительные блоки на месте.  
Вот как собрать из них сценарий:

```python
def open_and_verify_homepage(driver: WebDriver, logger: ILogger):
    """Open and verify my homepage."""
    on_homepage = Homepage(driver=driver)

    just_log_error = create_just_log_error(logger=logger)
    just_log_success = create_just_log_success(logger=logger)
    log_error_with_current_url = create_log_error_with_current_url(
        logger=logger, driver=driver
    )
    log_success_with_current_url_and_take_screenshot = (
        create_log_success_with_current_url_and_take_screenshot(
            logger=logger, driver=driver
        )
    )

    return [
        drive_page(
            act(on_homepage, open_homepage)
            .failure(just_log_error("Failed to open the homepage..."))
            .success(just_log_success("Opened the homepage!")),
            act(on_homepage, verify_homepage)
            .failure(
                log_error_with_current_url(
                    "Failed to verify the homepage...",
                )
            )
            .success(
                log_success_with_current_url_and_take_screenshot(
                    "Verified the homepage!"
                )
            ),
        ),
    ]


test_homepage = create_selenium_test(
    name="Validate homepage",
    test_scenario=lambda driver, logger: Scenario(
        test_chain=open_and_verify_homepage(driver, logger)
    ),
)
```

Каждый шаг теста выражается через `act`, к которому прицепляют обработчики `.failure()` и `.success()`.  
Затем сценарий оборачивается в объект `Test` с помощью `create_selenium_test`.

## 6. Создаём тестовый набор

Набор объединяет тесты, которые нужно прогнать на одном и том же пуле драйверов:

```python
def create_my_first_suite(
    *,
    drivers_pool: SeleniumWebDriversPool,
) -> TestSuite:
    """Create my first suite."""
    return TestSuite(
        name="My very first suite with Ocarina",
        tests=[
            test_homepage,
        ],
        drivers_pool=drivers_pool,
    )
```

## 7. Создаём тестовую кампанию

Кампания объединяет несколько наборов:

```python
def create_my_first_campaign(
    *, drivers_pool: SeleniumWebDriversPool
) -> TestCampaign:
    """Create my first campaign."""
    return TestCampaign(
        name="My very first campaign with Ocarina",
        suites=[
            create_my_first_suite(drivers_pool=drivers_pool),
        ],
    )
```

## 8. Создаём тестовый цикл

Цикл объединяет несколько кампаний. Это единица выполнения самого высокого уровня:

```python
E2E_CYCLE_NAME = "My very first cycle with Ocarina"

def create_my_first_cycle(drivers_pool: SeleniumWebDriversPool):
    """Create my first cycle."""
    return TestCycle(
        name=E2E_CYCLE_NAME,
        campaigns=[
            create_my_first_campaign(drivers_pool=drivers_pool),
        ],
    )
```

## 9. Запуск проекта

Вот полная точка входа в проект:

```python
if __name__ == "__main__":
    CliStoreSingleton().push(create_selenium_auto_cli_store())

    drivers_pool = create_selenium_drivers_pool(
        browser=get_browser(),
        driver_path=get_driver_path(),
        headless=get_headless(),
        wait_timeout=get_timeout(),
        max_size=get_max_workers(),
        profile_path=get_profile_path(),
    )

    def _post_exec(results: TestCycleResults) -> None:
        print()
        pretty_print_results(results, with_colors=True)
        if has_test_cycle_failed(results):
            sys.exit(1)

    with timing(prefix="Tests duration:"):
        bootstrap(
            post_exec=_post_exec,
            test_cycle=create_my_first_cycle(drivers_pool),
            run_plugins=lambda results: run_plugins(
                lambda: generate_docx_proof(
                    logs_root=get_default_log_dir() / E2E_CYCLE_NAME,
                    logger=create_matching_logger("terminal").set_domain_taxonomy(
                        ("Generate DOCX proofs plugin",)
                    ),
                    output_root=Path.cwd() / ".reports" / "tests_docx_output",
                ),
                lambda: generate_json_results(
                    results=results,
                    output_dir=Path.cwd() / ".reports" / "tests_json_output",
                    logger=create_matching_logger("terminal").set_domain_taxonomy(
                        ("Generate JSON report file plugin",)
                    ),
                ),
                exceptions_logger=PrintLogger()
                .set_prefix(
                    lambda: concat_metadata(
                        format_utc_date_metadata_str, format_current_thread_metadata_str
                    )
                )
                .set_domain_taxonomy(("Post-execution plugins",)),
            ),
        )
```

Процесс выглядит так:

1. Аргументы, полученные из CLI, помещаются в глобальное хранилище.
2. Создаётся пул драйверов: он управляет жизненным циклом веб-браузеров, работающих параллельно.
3. Определяется обратный вызов `_post_exec`: он срабатывает после тестов и плагинов, выводит результаты и завершается с кодом ошибки, если цикл
   провалился.
4. Вся загрузка происходит внутри таймера, измеряющего общую продолжительность выполнения. Таким образом, порядок выполнения такой:
   **цикл&nbsp;→&nbsp;плагины&nbsp;→&nbsp;post_exec**.

> ℹ️ Плагины — это отложенные функции, передаваемые в `run_plugins`.  
> `run_plugins` принимает `results` как аргумент —  
> и уже по одной сигнатуре функции сразу ясно, что выполняются они на этапе постобработки, как только результаты готовы.

<llm-exclude>

---

![Вы читаете Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До скорой встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Живите сейчас самими вопросами. Быть может, тогда, в один далёкий день, вы постепенно, сами того не замечая, вживётесь в ответ."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Райнер Мария Рильке</p>

</llm-exclude>
