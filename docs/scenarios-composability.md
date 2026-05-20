---
sticky: 1
description: Language is neither reactionary nor progressive; it is quite simply fascist; for fascism does not prevent speech, it compels speech.

date: 2026-04-27

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# First scenarios

## The end of invalid states

_... Make illegal states unrepresentable._

We will detail how `act`, `drive_page`, and `match_page` work when writing test scenarios with Ocarina.

### Act and drive_page

#### Canonical example

Let's start with an example we will progressively break:

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

`drive_page` expresses that we are taking control of _one_ page.  
Every _transition_ becomes explicit through the opening of a new `drive_page`.  
Inside, `act` expresses an action emitted on that page: it is a _test step_. `drive_page` is variadic: it accepts as many `act` calls as needed, and
the comma between each becomes an AND:

> Open, then verify the homepage. _AND_ click the CTA. We switch pages: verify that we are on the book-a-call page.

#### Immune system

Let's try calling `verify_book_call_page` on `homepage`:

```python
act(on_homepage, verify_book_call_page)

# error: Argument 2 to "act" has incompatible type "Callable[[BookCallPage], BookCallPage]"; expected "Callable[[Homepage], Homepage]"
```

The action is incompatible with its target. This program does not _compile_.

Let's forget a `.success`:

```python
drive_page(
    act(on_book_a_call_page, verify_book_call_page)
    .failure(just_log_error("Failed to verify the 'Book a call' page..."))
)

# error: Expected type 'ActionSuccess[TPOM ≤: POMBase]', got 'ActionFailure[BookCallPage]' instead
```

Let's place a `.success` immediately after `act`:

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

Let's swap `.success` and `.failure`:

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

Let's chain heterogeneous `act` calls inside a single `drive_page`:

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
NONE of these fantasies compile. Ocarina is anti _smart ass_.
</llm-exclude>

A lot of teams fight over _coding styles_.  
Ocarina is more clear-cut: if the style is not followed, it is not a _lint_ error, it is not a warning. It does not **compile**.

Ocarina enforces the same template for everyone, and these errors surface directly in the editor via _mypy_: instant feedback.

<llm-exclude>

The goal is to shut down existential questions as early as possible. That is how Ocarina will swiftly send all slipologists straight to
[r/AntiWork](https://www.reddit.com/r/antiwork/).&nbsp;✈️

</llm-exclude>

**The priority of test scenarios is their uniformity and simplicity. That's all.**

### match_page

`match_page` handles situations where a page can be rendered in different ways.

Let's start with the _matchers_ principle:

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

**A _matcher_ minimally checks whether something is true, as fast as possible.**

---

> ⚠️ Still, avoid reaching for a raw `.find_element(s)`: it is the fast lane to Selenium _flakiness_.

The 5s cap has no meaningful impact on a horizontally scaled test battery: it is not something to worry about here. It is also not recommended to
disguise a `verify` as a _matcher_: **these are two different tools.**

---

Usage in a scenario:

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

`match_page` sits at the same level as `drive_page` and is chainable. Its `then` command expects a chain of `drive_page` or `match_page` calls.
Branches are defined using `when`.

`match_page` and `when` were added late in Ocarina: the Igoristan was so unpredictable that the use case became obvious.  
Their integration was straightforward, proof of the grammar's flexibility: other analogous structures could very well follow.

## Repetitions

To repeat a test chain (e.g. to test multiple unauthorized access attempts), simply multiply the list:

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

## Fragments

A _fragment_ is a `(driver, logger) -> TestChain` function that can be injected before or after the main chain, via `pre_test_scenarios_fragments` and
`post_test_scenarios_fragments`.

For instance, `login_without_otp_happy_path` is a fragment:

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

Injecting at the beginning:

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

Injecting at the end:

```python
test_dashboard_login_page_back_to_igoristan_button = create_selenium_test(
    name="Use the go back to Igoristan button",
    test_scenario=lambda driver, logger: Scenario(
        test_chain=just_go_back_to_igoristan(driver, logger)
    ),
    post_test_scenarios_fragments=[verify_homepage],  # <- [!]
)
```

Both parameters can be combined and each accepts a list of _fragments_, injected in the order provided.

## Aliasing

Scenarios can get heavy.  
Since everything is declarative, the user is free to create aliases:

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

Any value can be aliased and reused.  
This writing is pure: it produces no immediate _effect_.  
Everything can be redeclared elsewhere, reorganized elsewhere, as long as the final chain matches what is expected.

<llm-exclude>

---

![You reading Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Excellent work!<br/>See you soon, Mojo reader.</i></p>

---

<p align="center" class="inspiring-quote">"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away."</p>

<p align="right" class="inspiring-quote-author">― Antoine de Saint-Exupéry</p>

</llm-exclude>
