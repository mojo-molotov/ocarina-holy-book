---
sticky: 1
description: Язык не реакционен и не прогрессивен — он попросту фашистский; ибо фашизм не запрещает говорить, он принуждает говорить.

date: 2026-04-27

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Первые сценарии

## Конец недопустимых состояний

_… Сделайте недопустимые состояния непредставимыми._

Разберём подробно, как `act`, `drive_page` и `match_page` работают при написании тестовых сценариев на Ocarina.

### Act и drive_page

#### Канонический пример

Начнём с примера, который будем постепенно ломать:

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

`drive_page` означает, что мы берём под контроль _одну_ страницу.  
Каждый _переход_ выражается явно — открытием нового `drive_page`.  
Внутри `act` выражает действие, совершаемое на этой странице: это _test step_. `drive_page` вариативен: он принимает сколько угодно вызовов `act`, а
запятая между ними превращается в AND:

> Открыть, затем проверить домашнюю страницу. _И_ кликнуть по CTA. Меняем страницу: проверить, что мы на странице book-a-call.

#### Иммунная система

Попробуем вызвать `verify_book_call_page` на `homepage`:

```python
act(on_homepage, verify_book_call_page)

# error: Argument 2 to "act" has incompatible type "Callable[[BookCallPage], BookCallPage]"; expected "Callable[[Homepage], Homepage]"
```

Действие несовместимо со своей целью. Эта программа не _компилируется_.

Забудем про `.success`:

```python
drive_page(
    act(on_book_a_call_page, verify_book_call_page)
    .failure(just_log_error("Failed to verify the 'Book a call' page..."))
)

# error: Expected type 'ActionSuccess[TPOM ≤: POMBase]', got 'ActionFailure[BookCallPage]' instead
```

Поставим `.success` сразу после `act`:

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

Поменяем местами `.success` и `.failure`:

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

Сцепим разнородные вызовы `act` внутри одного `drive_page`:

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
НИ ОДНА из этих выдумок не компилируется. Ocarina не выносит _умников_.
</llm-exclude>

Многие команды грызутся из-за _coding styles_.  
Ocarina не церемонится: если стиль не соблюдён — это не _lint_-ошибка и не предупреждение. Оно просто не **компилируется**.

Ocarina навязывает один и тот же шаблон всем, и эти ошибки всплывают прямо в редакторе — через _mypy_: мгновенная обратная связь.

<llm-exclude>

Цель — снять экзистенциальные вопросы как можно раньше. Вот так Ocarina быстро спровадит всех _slipologists_ прямо в
[r/AntiWork](https://www.reddit.com/r/antiwork/).&nbsp;✈️

</llm-exclude>

**Для тестовых сценариев в приоритете — однородность и простота. Только и всего.**

### match_page

`match_page` обрабатывает ситуации, когда страница может отрисовываться по-разному.

Начнём с принципа _matcher_'ов:

```python
@final
class PageWithCookiesBannerMatchers:
    """Drive nuts anybody with this page or use matchers."""

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

**_Matcher_ выполняет минимальную проверку того, истинно ли нечто, — и максимально быстро.**

---

> ⚠️ И всё же не хватайтесь за голый `.find_element(s)`: это прямая дорога к Selenium-_flakiness_.

Ограничение в 5 секунд почти не сказывается на горизонтально масштабируемой батарее тестов: тут об этом беспокоиться незачем. Не стоит и выдавать
`verify` за _matcher_: **это два разных инструмента.**

---

Применение в сценарии:

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

`match_page` стоит на одном уровне с `drive_page` и точно так же сцепляется в цепочки. Его команда `then` ждёт цепочку вызовов `drive_page` или
`match_page`. Ветви задаются через `when`.

`match_page` и `when` появились в Ocarina поздно: Igoristan оказался настолько непредсказуемым, что необходимость в них стала очевидной.  
Их интеграция прошла легко — доказательство гибкости грамматики: вполне могут появиться и другие подобные структуры.

## Повторения

Чтобы повторить тестовую цепочку (например, чтобы проверить несколько попыток несанкционированного доступа), просто умножьте список:

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

_Фрагмент_ — это функция `(driver, logger) -> TestChain`, которую можно внедрить до или после основной цепочки — через `pre_test_scenarios_fragments`
и `post_test_scenarios_fragments`.

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

Оба параметра можно комбинировать, и каждый принимает список _фрагментов_, которые внедряются в заданном порядке.

## Псевдонимы

Сценарии могут становиться громоздкими.  
Поскольку всё декларативно, пользователь волен заводить псевдонимы:

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

Любому значению можно дать псевдоним и переиспользовать его.  
Такая запись чистая: немедленного _эффекта_ она не производит.  
Всё можно переобъявить и перекомпоновать в другом месте — лишь бы итоговая цепочка соответствовала ожидаемой.

<llm-exclude>

---

![Вы читаете Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Отличная работа!<br/>До скорой встречи, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Совершенство достигается не тогда, когда уже нечего добавить, а когда уже нечего отнять."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Антуан де Сент-Экзюпери</p>

</llm-exclude>
