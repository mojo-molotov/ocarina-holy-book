---
sticky: 1
description: Язык — не реакционен и не прогрессивен; он попросту фашистский; потому что фашизм не препятствует речи, он заставляет говорить.

date: 2026-04-27

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Первые сценарии

## Конец недопустимых состояний

_... Сделайте недопустимые состояния непредставимыми._

Мы рассмотрим, как `act`, `drive_page` и `match_page` работают при написании тестовых сценариев с Ocarina.

### Act и drive_page

#### Канонический пример

Давайте начнём с примера, который мы постепенно сломаем:

```python
def go_from_homepage_to_book_call_page_with_the_cta(driver: WebDriver, logger: ILogger):
    """Open and verify my homepage."""
    on_homepage = Homepage(driver=driver)
    on_book_a_call_page = BookCallPage(driver=driver)

    just_log_error = create_just_log_error(logger=logger)
    just_log_success = create_just_log_success(logger=logger)
    log_success_with_current_url_and_take_screenshot = (
        create_log_success_with_current_url_and_take_screenshot(
            logger=logger, driver=driver
        )
    )

    return [
        drive_page(
            act(on_homepage, open_then_verify_homepage)
            .failure(just_log_error("Failed to reach the homepage..."))
            .success(
                log_success_with_current_url_and_take_screenshot(
                    "On the homepage!"
                )
            ),
            act(on_homepage, click_book_call_page_cta)
            .failure(just_log_error("Failed to click on the 'Book a call' CTA..."))
            .success(just_log_success("Clicked on the 'Book a call' CTA!")),
        ),
        drive_page(
            act(on_book_a_call_page, verify_book_call_page)
            .failure(just_log_error("Failed to verify the 'Book a call' page..."))
            .success(
                log_success_with_current_url_and_take_screenshot(
                    "On the 'Book a call' page!"
                )
            ),
        ),
    ]


test_homepage_book_a_call_cta = create_selenium_test(
    name="Go from homepage to book a call page, clicking the CTA",
    test_scenario=lambda driver, logger: Scenario(
        test_chain=go_from_homepage_to_book_call_page_with_the_cta(driver, logger)
    ),
)
```

`drive_page` выражает, что мы берём управление _одной_ страницы.  
Каждый _переход_ становится явным через открытие нового `drive_page`.  
Внутри, `act` выражает действие, выпущенное на этой странице: это _test step_. `drive_page` вариативен: он принимает столько вызовов `act`, сколько
нужно, и запятая между каждым становится AND:

> Открыть, затем проверить домашнюю страницу. _И_ кликнуть CTA. Мы переходим на страницу: проверить, что мы на странице book-a-call.

#### Иммунная система

Давайте попытаемся вызвать `verify_book_call_page` на `homepage`:

```python
act(on_homepage, verify_book_call_page)

# error: Argument 2 to "act" has incompatible type "Callable[[BookCallPage], BookCallPage]"; expected "Callable[[Homepage], Homepage]"
```

Действие несовместимо с его целью. Эта программа не _компилируется_.

Давайте забудем `.success`:

```python
drive_page(
    act(on_book_a_call_page, verify_book_call_page)
    .failure(just_log_error("Failed to verify the 'Book a call' page..."))
)

# error: Expected type 'ActionSuccess[TPOM ≤: POMBase]', got 'ActionFailure[BookCallPage]' instead
```

Давайте разместим `.success` сразу после `act`:

```python
drive_page(
    act(on_book_a_call_page, verify_book_call_page)
    .success(
        log_success_with_current_url_and_take_screenshot(
            "On the 'Book a call' page!"
        )
    ),
),

# error:
# "ActionStart[BookCallPage]" has no attribute "success"
# Unresolved attribute reference 'success' for class 'ActionStart'
```

Давайте поменяем местами `.success` и `.failure`:

```python
drive_page(
    act(on_book_a_call_page, verify_book_call_page)
    .success(
        log_success_with_current_url_and_take_screenshot(
            "On the 'Book a call' page!"
        )
    )
    .failure(just_log_error("Failed to verify the 'Book a call' page...")),
),

# error:
# "ActionStart[BookCallPage]" has no attribute "success"
# Unresolved attribute reference 'success' for class 'ActionStart'
```

Давайте объединим неоднородные вызовы `act` внутри одного `drive_page`:

```python
drive_page(
    act(on_homepage, open_then_verify_homepage)
    .failure(just_log_error("Failed to reach the homepage..."))
    .success(
        log_success_with_current_url_and_take_screenshot(
            "On the homepage!"
        )
    ),
    act(on_homepage, click_book_call_page_cta)
    .failure(just_log_error("Failed to click on the 'Book a call' CTA..."))
    .success(just_log_success("Clicked on the 'Book a call' CTA!")),
    act(on_book_a_call_page, verify_book_call_page)  # <- [!]
    .failure(just_log_error("Failed to verify the 'Book a call' page..."))
    .success(
        log_success_with_current_url_and_take_screenshot(
            "On the 'Book a call' page!"
        )
    ),
),

# error: Expected type 'ActionSuccess[Homepage]' (matched generic type 'ActionSuccess[TPOM ≤: POMBase]'), got 'ActionSuccess[BookCallPage]' instead
```

<llm-exclude>
НИ ОДНА из этих фантазий не компилируется. Ocarina против _умного ослабления_.
</llm-exclude>

Многие команды спорят о _coding styles_.  
Ocarina более ясна: если стиль не соблюдается, это не _lint_ ошибка, это не предупреждение. Это не **компилируется**.

Ocarina применяет один и тот же шаблон для всех, и эти ошибки непосредственно появляются в редакторе через _mypy_: мгновенная обратная связь.

<llm-exclude>

Цель — как можно раньше закрыть экзистенциальные вопросы. Вот как Ocarina быстро отправит всех slipologists прямо в
[r/AntiWork](https://www.reddit.com/r/antiwork/).&nbsp;✈️

</llm-exclude>

**Приоритет тестовых сценариев — их однородность и простота. Это всё.**

### match_page

`match_page` обрабатывает ситуации, когда страница может быть отображена по-разному.

Давайте начнём с принципа _matchers_:

```python
@final
class PageWithCookiesBannerMatchers:
    """Drive nut anybody with this page or use matchers."""

    def __init__(self, *, driver: WebDriver) -> None:
        """Initialize helper."""
        self._driver = driver

    def has_cookies_banner(self) -> bool:
        """Quickly verify if the cookies banner is displayed."""
        timeout = min(get_timeout(), 5)

        try:
            WebDriverWait(self._driver, timeout).until(
                ec.visibility_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="cookies-banner"]')
                )
            )
        except TimeoutException:
            return False
        return True

    def has_not_cookies_banner(self) -> bool:
        """Quickly verify if the cookies banner is NOT displayed."""
        timeout = min(get_timeout(), 5)

        try:
            WebDriverWait(self._driver, timeout).until(
                ec.invisibility_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="cookies-banner"]')
                )
            )
        except TimeoutException:
            return False
        return True
```

**_Matcher_ минимально проверяет, верно ли что-то, как можно быстрее.**

---

> ⚠️ Тем не менее, избегайте хвататься за сырой `.find_element(s)`: это прямая дорога к Selenium _flakiness_.

Ограничение в 5 секунд не оказывает значительного влияния на горизонтально масштабируемую батарею тестирования: это не то, о чём стоит беспокоиться
здесь. Также не рекомендуется маскировать `verify` как _matcher_: **это два разных инструмента.**

---

Использование в сценарии:

```python
on_homepage = Homepage(driver=driver)
check_that_page = PageWithCookiesBannerMatchers(driver=driver)

# * ...
[
    match_page(
        branches=[
            when(
                check_that_page.has_cookies_banner,
                name="Has cookies banner",
                then=[
                    drive_page(
                        act(on_homepage, confirm_cookie_banner)
                        .failure(
                            log_error_with_current_url(
                                "Failed to click on the cookies banner's confirm button..."
                            )
                        )
                        .success(
                            log_success_with_current_url_and_take_screenshot(
                                "Clicked on the cookies banner's confirm button!"
                            )
                        )
                    )
                ],
            ),
            when(
                check_that_page.has_not_cookies_banner,
                name="Has NOT cookies banner",
                then=[],
            ),
        ],
        logger=create_matching_logger("terminal"),  # <- [!] If you want debug logs
    ),
    drive_page(
        act(on_homepage, ...)
        .failure(...)
        .success(...)
    ),
]
```

`match_page` находится на одном уровне с `drive_page` и компонуется так же. Его команда `then` ожидает цепь вызовов `drive_page` или `match_page`.
Ветви определяются с помощью `when`.

`match_page` и `when` были добавлены поздно в Ocarina: Igoristan был настолько непредсказуем, что вариант использования стал очевидным.  
Их интеграция была простой, доказательство гибкости грамматики: другие аналогичные структуры вполне могут следовать.

## Повторения

Чтобы повторить цепь тестирования (например, чтобы протестировать несколько попыток несанкционированного доступа), просто умножьте список:

```python
[
    drive_page(
        act(on_dashboard_welcome_page, click_on_go_to_nested_page_btn)
        .failure(
            just_log_error("Failed to click on the go-to-nested-page button...")
        )
        .success(just_log_success("Clicked on the go-to-nested-page button!")),
        act(on_dashboard_welcome_page, verify_missing_otp_msg_is_displayed)
        .failure(
            just_log_error(
                "Failed to find the missing OTP auth message...",
            )
        )
        .success(
            log_success_with_current_url_and_take_screenshot(
                "Found the missing OTP auth message!"
            )
        ),
    ),
] * 5  # <- [!]
```

## Фрагменты

_Фрагмент_ — это функция `(driver, logger) -> TestChain`, которую можно внедрить до или после основной цепи, через `pre_test_scenarios_fragments` и
`post_test_scenarios_fragments`.

Например, `login_without_otp_happy_path` — это фрагмент:

```python
def login_without_otp_happy_path(driver: WebDriver, logger: ILogger):
    """Verify that we can connect without OTP."""
    on_dashboard_login_page = DashboardLoginPage(driver=driver)
    on_dashboard_welcome_page = DashboardWelcomePage(driver=driver)

    # * ...
    return [
        drive_page(
            act(on_dashboard_login_page, open_dashboard_login_page)
            .failure(just_log_error("Failed to open the dashboard login page..."))
            .success(just_log_success("Opened the dashboard login page!")),
            # * ...
        ),
        # * ...
    ]
```

Внедрение в начале:

```python
test_cant_access_the_protected_page_without_otp_using_the_ui = create_selenium_test(
    name="Can't access the protected page without OTP (using the UI)",
    test_scenario=lambda driver, logger: Scenario(
        test_chain=dashboard_access_to_protected_page_without_otp_using_the_ui(
            driver, logger
        )
    ),
    pre_test_scenarios_fragments=[login_without_otp_happy_path],  # <- [!]
)
```

Внедрение в конце:

```python
test_dashboard_login_page_back_to_igoristan_button = create_selenium_test(
    name="Use the go back to Igoristan button",
    test_scenario=lambda driver, logger: Scenario(
        test_chain=just_go_back_to_igoristan(driver, logger)
    ),
    post_test_scenarios_fragments=[verify_homepage],  # <- [!]
)
```

Оба параметра можно комбинировать, и каждый принимает список _фрагментов_, внедряемых в указанном порядке.

## Псевдонимы

Сценарии могут стать тяжёлыми.  
Поскольку всё декларативно, пользователь волен создавать псевдонимы:

```python
on_homepage = Homepage(driver=driver)
check_that_page = PageWithCookiesBannerMatchers(driver=driver)

click_confirm_cookies = drive_page(
    act(on_homepage, confirm_cookie_banner)
    .failure(
        log_error_with_current_url(
            "Failed to click on the cookies banner's confirm button..."
        )
    )
    .success(
        log_success_with_current_url_and_take_screenshot(
            "Clicked on the cookies banner's confirm button!"
        )
    )
)

# * ...
[
    match_page(
        branches=[
            when(
                check_that_page.has_cookies_banner,
                name="Has cookies banner",
                then=[click_confirm_cookies],  # <- [!]
            ),
            when(
                check_that_page.has_not_cookies_banner,
                name="Has NOT cookies banner",
                then=[],
            ),
        ],
        logger=create_matching_logger("terminal"),  # <- [!] If you want debug logs
    ),
    drive_page(
        act(on_homepage, ...)
        .failure(...)
        .success(...)
    ),
]
```

Любое значение можно сделать псевдонимом и переиспользовать.  
Это написание чистое: оно не производит немедленного _эффекта_.  
Всё можно переобъявить в другом месте, переорганизовать в другом месте — лишь бы итоговая цепь соответствовала ожидаемому.

<llm-exclude>

---

![You reading Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До скорой встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Совершенство достигается не тогда, когда нечего больше добавить, а когда нечего больше убрать."</p>

<p align="right" class="inspiring-quote-author">― Антуан де Сент-Экзюпери</p>

</llm-exclude>
