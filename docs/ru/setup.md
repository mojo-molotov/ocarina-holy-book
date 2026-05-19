---
sticky: 1
description: Речь идет не о пункте назначения, а о путешествии.

date: 2026-04-26

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Первые шаги

## Отказ от ответственности

> **Примечание:** Эта книга предназначена, чтобы помочь вам познакомиться с предоставленным проектом `ocarina-example`, который остается **источником
> истины**, на который следует ссылаться во всех обстоятельствах.

> ⚠️ _The Ocarina Holy Book_ НЕ является и никогда не будет "plug-and-play". Ocarina требует высокого уровня зрелости для использования. Поэтому мы
> сосредоточимся только на том, что действительно может быть трудным.

Эта страница объясняет _путешествие_. После этого будет необходима практика.  
[📖 Получите канонический пример в качестве справки.](https://github.com/mojo-molotov/ocarina-example)

## 1. Настройка проекта

Создайте новый проект Python, затем установите необходимые зависимости:

```bash
pip install selenium
pip install ocarina
```

Затем создайте структуру папок.

## 2. Адаптеры

Ocarina построена вокруг системы адаптеров, которые пользователь отвечает за написание. Они позволяют фреймворку быть настроенным в соответствии с
ограничениями и соглашениями каждого проекта.

Основные адаптеры, которые нужно создать:

- `act` _(требуется)_
- `test_campaign` _(требуется)_
- `test_suite` _(требуется)_
- `env_getters` _(опционально)_
- `match_page` _(опционально)_

### 2.1 EnvGetters

`EnvGetters` Ocarina централизует и типизирует доступ к переменным окружения. Он разделён на две категории:

- **Creds**: пары логин/пароль, выраженные как неизменяемые словари.
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

Как только этот адаптер будет на месте, получение значения или учетных данных выглядит так:

```python
xxxxx_url = create_env_getters().get_value("xxxxx_url")
dashboard_creds = create_env_getters().get_credentials("dashboard")
print(xxxxx_url)
print(dashboard_creds["login"])
print(dashboard_creds["password"])
```

> **Примечание:** Допустимые ключи предоставляются через два типа: `EnvGetters[_CredsKeys, _ValuesKeys]`. Если пользователь хочет использовать только
> `.get_value()`, достаточно типизировать `_CredsKeys` как `Never`. То же самое относится к `_ValuesKeys`, которые должны быть типизированы как
> `Never`, если пользователь хочет использовать только `.get_credentials()`.

Наши акцессоры строго типизированы. Например:

```python
xxxxx_url = create_env_getters().get_value("x")

# error: Argument 1 to "get_value" of "EnvGetters" has incompatible type "Literal['x']"; expected "Literal['igor_xxx_key', 'xxxxx_url']"
```

### 2.2 Act

В Ocarina, `act` — это глагол, используемый для выражения каждого отдельного шага в тестовом сценарии. Его конструкция намеренно оставлена
пользователю, по причинам, освещённым далее в этой книге (_hooks_).

Его минимальная форма выглядит следующим образом:

```python
def act(pom: TPOM, action: Callable[[TPOM], TPOM]) -> ActionStart[TPOM]:
    """Act on a page."""

    return create_act(
        pom,
        action,
    )
```

### 2.3 TestCampaign

Адаптер `TestCampaign` намеренно минималистичен. Единственная информация, которую Ocarina не может вывести, — это **количество рабочих потоков**, то
есть количество браузеров для параллельного запуска для данной кампании. Поскольку этот параметр также может быть передан непосредственно через CLI,
необходимо только небольшое приложение:

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

> Тип `WebDriver` (Selenium или иначе) вводится здесь: `OriginalTestCampaign[WebDriver]`.  
> И здесь: `suites: Sequence[TestSuite[WebDriver]]`

> ✅ Конечно, вставьте ВАШ адаптированный `TestSuite` здесь, а не встроенный в Ocarina.

### 2.4 TestSuite

Это самый важный адаптер для понимания. `TestSuite` нативно выставляет большое количество параметров. Цель этого адаптера — создать **фасад** вокруг
него: некоторые значения жестко закодированы раз и навсегда, другие опционально выставлены с разумными значениями по умолчанию. _Сужение_.

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

> Тип `WebDriver` (Selenium или иначе) вводится здесь: `OriginalTestSuite[WebDriver]`.  
> Также здесь: `tests: Sequence[Test[WebDriver]]`  
> И здесь: `drivers_pool: SeleniumWebDriversPool`

#### Временные ошибки

Концепция `transient_errors` имеет центральное значение для `TestSuite`.  
Эти ошибки рассматриваются как **помехи**: если тест не прошел из-за исключения, указанного в `transient_errors`, он автоматически повторяется.  
Максимальное количество попыток определяется `max_retries_per_test`.

Этот механизм делает выполнение тестов устойчивым к _flakiness_. Тесты, которые повторяются часто, четко видны в логах, позволяя разработчикам
выявлять и исправлять источники нестабильности, вызванные неправильным использованием Selenium, условиями окружения вне области действия или другими
внешними факторами.

#### Только ID и исключить ID

Эти два параметра позволяют условное выполнение тестов.  
Они являются фильтрами на основе ID.

> ⚠️ **Убедитесь, что включили их в этот адаптер, иначе эти флаги CLI не будут обработаны.**

### 2.5 MatchPage

`match_page` — это оператор Ocarina, разработанный для обработки страниц с недетерминированным рендерингом: баннеры cookie, антибот-вызовы, A/B тесты
и т. д.

Его логика проста: **любое поднятое исключение интерпретируется как несовпадение и поэтому поглощается `match_page`**. Однако возможно исключить
некоторые исключения из этого механизма, чтобы они распространялись нормально вверх по потоку выполнения.

Для согласованности `transient_errors` обычно должны попадать в эту категорию: они должны распространяться, а не молча подавляться.

Адаптер создается следующим образом:

```python
match_page = create_match_page(raised_exceptions=transient_errors)
```

## 3. Написание первого POM

Паттерн POM (_Page Object Model_) является хорошо установленным стандартом, который мы не будем переопределять здесь.

Вот как создать первый POM с Ocarina:

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

Несколько моментов стоит детализировать.

### 3.1 SeleniumTitleMixin

Любой объект, наследующий `POMBase`, должен реализовать метод `get_current_title`. `SeleniumTitleMixin` предоставляет эту реализацию прозрачно, без
необходимости писать её вручную.

Его роль идет дальше: он также определяет атрибут `_driver` с типом `WebDriver` (Selenium), делая его **несовместимым с любым другим типом**. Попытка
присвоить неправильное значение немедленно вызовет ошибку типа:

```python
self._driver = "lol"

# error: Incompatible types in assignment (expression has type "str", variable has type "WebDriver")
```

`SeleniumTitleMixin` также действует как **страж типа**. Аналогичные миксины могут быть созданы для других технологий браузерной автоматизации.

### 3.2 Возврат `self`

Каждый метод действия возвращает `self`. Это намеренный выбор конструкции в Ocarina, который следует последовательно соблюдать: он позволяет связывать
методы в цепочки и плавно компоновать сценарии.

## 4. Написание соединителей

Соединители — это тонкий, но важный слой для читаемости сценариев. Они обертывают вызовы методов POM в явно названные функции:

```python
def open_homepage(p: Homepage) -> Homepage:
    """Open my homepage."""
    return p.open()


def verify_homepage(p: Homepage) -> Homepage:
    """Verify we are on my homepage."""
    return p.verify()
```

Они также могут быть составлены напрямую:

```python
def open_then_verify_homepage(p: Homepage) -> Homepage:
    """Open my homepage, then verify it."""
    return p.open().verify()
```

## 5. Написание первого тестового сценария

Все строительные блоки готовы.  
Вот как собрать их в сценарий:

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

Каждый шаг тестирования выражается через `act`, к которому привязаны обработчики `.failure()` и `.success()`.  
Затем сценарий оборачивается в объект `Test` через `create_selenium_test`.

## 6. Создание тестовой суиты

Суита группирует набор тестов, которые должны быть выполнены против одного и того же пула драйверов:

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

## 7. Создание тестовой кампании

Кампания группирует несколько суит:

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

## 8. Создание тестового цикла

Цикл группирует несколько кампаний. Это единица выполнения наивысшего уровня:

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

## 9. Загрузка проекта

Вот полная точка входа для проекта:

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

Процесс выглядит следующим образом:

1. Аргументы, полученные из CLI, передаются в глобальное хранилище.
2. Создается пул драйверов: он управляет жизненным циклом веб-браузеров, работающих параллельно.
3. Определяется обратный вызов `_post_exec`: он запускается после тестов и плагинов, выводит результаты и выходит с кодом ошибки, если цикл не прошел.
4. Всё загружается внутри таймера, измеряющего общую продолжительность выполнения. Поток выполнения, таким образом: **цикл → плагины → post_exec**.

> ℹ️ Плагины — это отложенные функции, переданные `run_plugins`.  
> `run_plugins` принимает `results` в качестве аргумента,  
> что сразу ясно из сигнатуры функции, что они запускаются как постобработка, как только результаты доступны.

<llm-exclude>

---

![Вы читаете Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Живите сейчас самими вопросами. Быть может, тогда, спустя долгие годы, вы незаметно для себя войдёте в ответ."</p>

<p align="right" class="inspiring-quote-author">― Райнер Мария Рильке</p>

</llm-exclude>
