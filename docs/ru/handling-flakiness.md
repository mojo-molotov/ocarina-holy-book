---
sticky: 1
description: Единственным разумным решением было приспособиться к существующим условиям.

date: 2026-04-29

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Первые реальные препятствия

<llm-exclude>
Добро пожаловать, дорогой друг.
</llm-exclude>

## Случайные ошибки сервера

Случайные ошибки сервера — крепкий орешек.  
На одной особенно неприятной работе мне пришлось иметь дело с окружением, которое регулярно выдавало совершенно случайные страницы ошибки 500 — в
какой бы раздел приложения ты ни зашёл.

В таких случаях ответ Ocarina кроется прямо в том, как создаётся глагол `act`:

```python
ERROR_PAGE_REGEX = re.compile(r"^\d{3}(?!\d)")

@final
class HttpErrorPageReachedError(Exception):
    """Raised when error page is reached."""

def act(pom: TPOM, action: Callable[[TPOM], TPOM]) -> ActionStart[TPOM]:
    """Act on a page."""

    def failure_hook(pom: TPOM, exc: Exception) -> Fail:
        with suppress(Exception):
            title = pom.get_current_title()
            is_http_error_page = title and ERROR_PAGE_REGEX.match(title.strip())
            if is_http_error_page:
                http_error = HttpErrorPageReachedError(f"HTTP error page: {title}")
                http_error.__cause__ = exc
                return Fail(error=http_error)
        return Fail(error=exc)

    return create_act(
        pom,
        action,
        on_failure=failure_hook,  # <- [!]
    )
```

Хук `on_failure` создан именно для этого.  
Достаточно завести несколько _предохранителей_ и подменить ошибку, обёрнутую в `Fail`, — чтобы запустить _повторный прогон_ любого теста, упавшего по
внешней причине.

Следующий шаг должен быть вам знаком:

```python
transient_errors = (
    HttpErrorPageReachedError,  # <- [!]
    PageVerificationError,
    # * ...
)

@final
class TestSuite(OriginalTestSuite[WebDriver]):
    """TestSuite adapter."""

    def __init__(
        self,
        *,
        # * ...
    ) -> None:
        """Initialize the TestSuite."""
        # * ...
        super().__init__(
            # * ...
            max_retries_per_test=8,
            transient_errors=transient_errors,
        )
```

Наконец, если в проекте используется ещё и `match_page`, а общая переменная `transient_errors` нежелательна, не забудьте добавить эти новые классы
ошибок в параметр `raised_exceptions` конструктора `match_page`.

Логи автотестов станут хорошей отправной точкой, чтобы поднять эти проблемы перед командой.

## Случайные ошибки в пределах шага

Решив, что вся эта дичь осталась позади, я двинулся дальше — и тут же наткнулся на нестабильные формы и системы аутентификации, которые работали через
раз.

Здесь ответ Ocarina иной: ответственность мы передаём POM-у.

```python
@final
class CorsicamonEnterXXXKeyPage(SeleniumTitleMixin, POMBase):
    """Igoristan's corsicamon enter XXX key page."""

    def enter_xxx_key(
        self
    ) -> CorsicamonEnterXXXKeyPage:
        """Enter XXX key."""
        # * ...

    # * ...
    def enter_xxx_key_with_retries(
        self, *, retries: int, logger: ILogger
    ) -> CorsicamonEnterXXXKeyPage:
        """Enter XXX key (n retries)."""
        validate(retries, name="retries").assert_that(
            is_positive
        ).execute().raise_if_invalid()

        attempts_count = 1
        self.enter_xxx_key()

        while attempts_count <= retries:
            timeout = get_timeout()
            with suppress(Exception):
                WebDriverWait(self._driver, timeout).until(
                    ec.invisibility_of_element_located(
                        self._corsicamon_network_error_container
                    )
                )
                break

            msg = (
                "Failed to enter the XXX Key."
                "\n"
                f"Life: {attempts_count}/{retries}"
                "\n"
                f"Current URL: {self._driver.current_url}"
            )

            logger.warning(msg)
            take_screenshot(driver=self._driver, logger=logger, category="WARNING")
            self.click_retry_button()
            attempts_count += 1

        s = "s" if attempts_count > 1 else ""
        msg = f"Entered the XXX Key. After {attempts_count} attempt{s}."

        logger.info(msg)
        return self
```

Тут же встаёт вопрос о _connectors_: как передавать в них параметры?

```python
"""Functional connectors."""

# * ...

def enter_xxx_key(
    p: CorsicamonEnterXXXKeyPage,
) -> CorsicamonEnterXXXKeyPage:
    """Enter the XXX key."""
    return p.enter_xxx_key()

# * ...

def enter_xxx_key_with_retries(
    *,
    retries: int,
    logger: ILogger,
) -> Callable[[CorsicamonEnterXXXKeyPage], CorsicamonEnterXXXKeyPage]:
    """Click on the retry button."""

    def unwrapped(p: CorsicamonEnterXXXKeyPage) -> CorsicamonEnterXXXKeyPage:
        return p.enter_xxx_key_with_retries(retries=retries, logger=logger)

    return unwrapped
```

Просто верните `def` с нужной сигнатурой — изнутри функции, которая захватывает параметры.  
Это и есть [_closure_](<https://en.wikipedia.org/wiki/Closure_(computer_programming)>).

## Случайные ошибки Selenium

Selenium даёт массу возможностей выстрелить себе в ногу: _race conditions_, ошибки _stale element_ и так далее.

Ответ здесь **прагматичный**: добавьте `WebDriverException` прямо в `transient_errors` — со щедрым числом повторов (8, то есть 9 жизней, как у кошки
🐱).

Перехватывайте все ошибки Selenium и следите за повторами в логах.  
После этого легко вычислить тесты, которые не помешало бы доработать.

## Дискретные случайные ошибки

Ещё удивительнее: приложения, которые без видимой причины показывают тосты с ошибками, или формы, которые ругаются ошибками валидации на совершенно
корректный ввод — при этом реально ничего не блокируя.

Эти ошибки поймать труднее всего — именно потому, что они _безболезненны_. Тут не получится просто увидеть падение и навесить _политику повторов_,
пока баг не починят. По сути, они невидимы.

Что остаётся? Кромсать тестовые сценарии или хвататься за «ниндзя-техники».  
Ocarina отвергает и то, и другое.

Используйте _watchers_:

```python
def catch_me_if_you_can_cb(watcher: SeleniumWatcher) -> None:
    """Detect any element with CSS class 'catch-me-if-you-can' on the current page."""
    # NOTE: using JS here to bypass the implicit wait timeout.
    elements = watcher.driver.execute_script(
        "return Array.from(document.querySelectorAll('.catch-me-if-you-can'));"
    )

    if not elements:
        return

    raw = watcher.driver.execute_script(
        """
        return arguments[0].map(el => ({
            tag:       el.tagName.toLowerCase(),
            text:      el.innerText.trim(),
            id:        el.id,
            cls:       el.className,
            name:      el.getAttribute('name') || '',
            testid:    el.getAttribute('data-testid') || '',
        }));
        """,
        elements,
    )

    for attrs in raw:
        fingerprint = ":".join(
            filter(
                None,
                [
                    attrs["tag"],
                    attrs["text"],
                    attrs["id"],
                    attrs["cls"],
                    attrs["name"],
                    attrs["testid"],
                ],
            )
        )

        if fingerprint in watcher.cache:
            continue

        watcher.cache.add(fingerprint)
        watcher.report(
            f"catch-me-if-you-can element detected: <{attrs['tag']}> {attrs['text']!r}",
            label="CATCH_ME_IF_YOU_CAN",
        )

# * ...

test_send_chaotic_form = create_selenium_test(
    name="Send the chaotic form",
    test_scenario=lambda driver, logger: Scenario(
        test_chain=_send_chaotic_form(
            HumanizedDriver(
                driver,
                wpm=125,
                typo_rate=0.14,
                hesitation_rate=0.02,
                burst_rate=0.35,
                late_correction_rate=0.6,
            ),
            logger,
        ),
        watchers=[  # <- [!]
            create_selenium_watcher(
                callback=catch_me_if_you_can_cb,
                name="catch-me-if-you-can",
                poll_interval=0.8,
            ),
        ],
    ),
)
```

`catch_me_if_you_can_cb` — это _callback_, который _watcher_ вызывает каждые 0,8 секунды (`poll_interval`).

Уточним несколько моментов.

### Использование JS

_Watcher_ устойчив к ошибкам: исключения он молча проглатывает.  
Поэтому нет смысла брать функцию Selenium, чтобы достать элемент страницы, — это лишь добавило бы лишнего балласта.  
А родные функции Selenium заставили бы возиться с _implicit timeout_.

Если идти напрямую через _Javascript_, это обходит всю внутреннюю логику _polling_ и делает работу _watcher_ максимально неблокирующей для теста,
который выполняется на том же _driver_.

Весь трюк остаётся незаметным — он занимает всего несколько миллисекунд.

### Отпечатки

_Watchers_ предоставляют простой строковый кэш, созданный как раз под эту задачу: если одна и та же ошибка остаётся на виду и фиксируется каждые 0,8
секунды, нет смысла снова и снова натыкаться на неё в скриншотах, отчётах и логах. Отпечаток позволяет пропускать то, что вы уже видели.

### Отчёт

В конце _callback_ вызывает `watcher.report`.  
Этот вызов берёт на себя:

1. запись в лог того трения, которое обнаружил _watcher_;
2. создание скриншота — как следа обнаруженного.

### HumanizedDriver

Ничто не мешает нам навешивать поведение на _logger_ или _driver_. Здесь, раз уж форма капризная, мы выбираем медленный, «очеловеченный» тест: ввод
текста с опечатками, исправлениями и заминками. Мы просто оборачиваем _driver_ в _proxy_ — `HumanizedDriver`.

## Гейзенбаги конкурентности

Мои поиски на этом не закончились.  
Как-то раз, прямо там, в офисе, я наблюдал, как коллеги считают до трёх, чтобы потом разом кликнуть и запустить одно и то же действие. Я поймал себя
на мыслях о смысле собственной жизни. И всё же таким способом они и правда умудрялись воспроизводить баги.

Это поведение можно воспроизвести и средствами Ocarina.  
По умолчанию Ocarina агрессивна.

Её опция `saturate_workers` принудительно и случайным образом клонирует тесты внутри набора.  
Всякий раз, когда в _DriversPool_ доступно больше _workers_, чем тестов для прогона в наборе, Ocarina случайным образом наклонирует тесты, поднимет
все драйверы и раздаст каждому по тесту.

Эту опцию можно включить из функции `bootstrap`. Её также можно переключать точечно — на уровне набора или кампании.  
При конфликте последнее слово за самым глубоким элементом иерархии.  
Например, если кампания опцию отключает, а набор включает, приоритет за набором.

```python
if __name__ == "__main__":
    with timing(prefix="Tests duration:"):
        bootstrap(
            saturate_workers=False,  # <- True by default
            # * ...
        )

# * ...
def create_campaign(
    *, drivers_pool: SeleniumWebDriversPool
) -> TestCampaign:
    return TestCampaign(
        saturate_workers=True,  # <- 'None' by default (cascade)
        max_workers=16,  # <- 'None' by default (CLI value)
        # ⬆️ Forcing saturate workers policy and 16 workers on this campaign.
        # * ...
    )

# * ...
def create_suite(
    *,
    drivers_pool: SeleniumWebDriversPool,
) -> TestSuite:
    return TestSuite(
        saturate_workers=False,  # <- 'None' by default (cascade)
        # ⬆️ Will take the priority: saturate workers disabled on this suite.
        # * ...
    )
```

Можно также временно собрать набор из одного-единственного теста — чтобы добиться предельной точности нацеливания.  
Или запустить цикл сразу на нескольких машинах (горизонтальное масштабирование).

Помимо вопросов конкурентности, этот механизм клонирования призван ещё и гарантировать, что проходящие тесты ничем не обязаны случайности. И эффект
тем сильнее, чем выше степень горизонтального масштабирования и чем больше задействовано workers.

<llm-exclude>

---

![Вы читаете Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До скорой встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Retry flaky blocks."</p>

<p align="right" class="inspiring-quote-author">― Егор Бугаенко, <i><a href="https://github.com/yegor256/prompt" target="_blank" rel="noreferrer">Prompt</a></i></p>

</llm-exclude>
