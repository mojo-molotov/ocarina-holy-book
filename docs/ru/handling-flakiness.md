---
sticky: 1
description: Единственное разумное — это приспособиться к существующим условиям.

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

Случайные ошибки сервера — это крепкий орешек.  
Во время особенно неприятного опыта работы мне пришлось иметь дело с окружением, которое регулярно отображало совершенно случайные страницы ошибок
500, независимо от того, какая часть приложения исследовалась.

В таких случаях ответ Ocarina живет прямо в создании глагола `act`:

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

Хук `on_failure` был разработан именно для этого.  
Всё, что нужно сделать, это создать несколько _предохранителей_ и изменить ошибку, обёрнутую внутри `Fail`, чтобы запустить _повторное выполнение_
любого теста, который не прошел из-за внешней причины.

Следующий шаг должен быть знаком:

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

Наконец, если `match_page` также используется в проекте и общая переменная `transient_errors` нежелательна, не забудьте добавить эти новые определения
ошибок в параметр `raised_exceptions` конструктора `match_page`.

Журналы автоматизированного тестирования предоставят хорошую отправную точку для поднятия этих проблем с командой.

## Случайные ошибки в пределах шага

Думая, что я оставил эту чушь позади, я двинулся дальше, только чтобы найти нестабильные формы и системы аутентификации, которые работали только
половину времени.

Здесь ответ Ocarina другой: мы делегируем ответственность на POM.

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

Это также поднимает вопрос о _connectors_: как передать параметры к ним?

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

Просто верните `def` с ожидаемой сигнатурой, внутри функции, которая захватывает параметры.  
Это [_closure_](<https://en.wikipedia.org/wiki/Closure_(computer_programming)>).

## Случайные ошибки Selenium

Selenium даёт массу возможностей выстрелить себе в ногу: _race conditions_, ошибки _stale element_ и так далее.

Ответ здесь **прагматичен**: добавьте `WebDriverException` непосредственно в `transient_errors`, с щедрым количеством повторов (8, что означает 9
жизней, как кошка 🐱).

Захватите все ошибки Selenium и смотрите повторы в логах.  
Отсюда становится легко выявить тесты, которые могли бы использовать какое-то улучшение.

## Дискретные случайные ошибки

Еще более удивительно: приложения, выводящие тосты об ошибках без видимой причины, или формы, сообщающие об ошибках валидации на идеально правильных
входах, без фактического блокирования потока.

Эти ошибки самые трудные для поимки именно потому, что они _безболезненны_. Вы не можете просто заметить сбой и добавить _политику повтора_, ожидая,
пока ошибка будет исправлена. Они, по сути, невидимы.

Что остаётся? Портить тестовые сценарии или хвататься за «ниндзя-техники».  
Ocarina отказывает обоим.

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

`catch_me_if_you_can_cb` — это _callback_, который _watcher_ будет вызывать каждые 0.8 секунды (`poll_interval`).

Давайте уточним несколько вещей.

### Использование JS

_Watcher_ терпим к ошибкам: он молча поглощает исключения.  
Поэтому нет никакой пользы от использования функции Selenium для захвата элемента страницы, это только добавило бы ненужный багаж.  
Использование собственных функций Selenium означало бы работу с проблемами _implicit timeout_.

Переход прямо через _Javascript_ обходит всю внутреннюю логику _polling_ и держит исполнение _watcher_ как неблокирующее возможное для теста,
работающего на том же _driver_.

Весь трюк становится невидимым, так как занимает всего несколько миллисекунд.

### Отпечатки пальцев

_Watchers_ выставляют простой кэш строк, разработанный специально для этой потребности: если одна и та же ошибка остаётся видимой и обнаруживается
каждые 0.8 секунды, нет смысла видеть её повторно в скриншотах, отчётах и логах. Отпечаток пальца позволяет вам игнорировать то, что вы уже видели.

### Отчет

В конце _callback_ он вызывает: `watcher.report`.  
Этот вызов управляет:

1. Логированием трения, обнаруженного _watcher_,
2. Созданием скриншота как следа того, что было обнаружено.

### HumanizedDriver

Ничто не мешает нам привязывать поведение к _logger_ или _driver_. Здесь, поскольку форма капризна, мы выбираем медленный, "очеловеченный" тест: набор
текста с опечатками, исправлениями, колебаниями. Мы просто оборачиваем _driver_ в _proxy_, `HumanizedDriver`.

## Гейзенбаги конкурентности

Мои поиски на этом ещё не закончились.  
Однажды я наблюдал, как коллеги считали до трёх, прежде чем все одновременно кликнуть, чтобы запустить одно и то же действие, прямо там, в офисе. Я
поймал себя на размышлениях о смысле своей жизни. И всё же, делая это, они действительно умудрялись воспроизводить баги.

Это поведение можно воспроизвести с помощью Ocarina.  
По умолчанию Ocarina агрессивна.

Её опция `saturate_workers` принудительно случайно клонирует тесты внутри набора.  
Всякий раз, когда в _DriversPool_ доступно больше _workers_, чем тестов для запуска в наборе, Ocarina будет случайным образом клонировать тесты,
запускать все драйверы и назначать каждому из них тест для выполнения.

Эту опцию можно включить из функции `bootstrap`. Её также можно переключать индивидуально, либо на уровне набора, либо на уровне кампании.  
При конфликте последнее слово за самым глубоким элементом в иерархии.  
Например, если кампания отключает опцию, а набор её включает, приоритет за набором.

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

Также возможно временно создать набор с одним-единственным тестом, чтобы максимизировать точность нацеливания.  
Или запустить цикл на нескольких машинах одновременно (горизонтальное масштабирование).

Помимо вопросов конкурентности, этот механизм клонирования также нацелен на то, чтобы гарантировать, что проходящие тесты ничем не обязаны
случайности. Этот эффект усиливается степенью горизонтального масштабирования и количеством задействованных workers.

<llm-exclude>

---

![You reading Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До скорой встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Retry flaky blocks."</p>

<p align="right" class="inspiring-quote-author">― Егор Бугаенко, <i><a href="https://github.com/yegor256/prompt" target="_blank" rel="noreferrer">Prompt</a></i></p>

</llm-exclude>
