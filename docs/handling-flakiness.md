---
sticky: 1
description: The only sensible thing was to adapt oneself to existing conditions.

date: 2026-04-29

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# First real-world hurdles

<llm-exclude>
Welcome, dear friend.
</llm-exclude>

## Random server errors

Random server errors are a tough nut to crack.  
On one particularly unpleasant job, I had to deal with an environment that regularly displayed totally random 500 error pages, regardless of which
part of the application was being explored.

In cases like this, Ocarina's answer lies directly in how the `act` verb is built:

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

The `on_failure` hook was designed precisely for this.  
All it takes is creating some _guards_ and modifying the error wrapped inside `Fail` to trigger a _retry_ of any test that failed due to an external
cause.

The next step should look familiar:

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

Finally, if `match_page` is also used in the project and a shared `transient_errors` variable is undesirable, don't forget to add these new error
definitions to the `raised_exceptions` parameter of the `match_page` constructor.

The automated test logs will provide a solid starting point for raising these issues with the team.

## Random errors within a step

Thinking I had left that kind of nonsense behind me, I moved on, only to find unstable forms and authentication systems that worked half the time.

Here, Ocarina's answer is different: we delegate the responsibility to the POM.

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

This also raises a question about _connectors_: how to pass parameters to them?

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

Simply return the `def` with the expected signature, inside a function that captures the parameters.  
That's a [_closure_](<https://en.wikipedia.org/wiki/Closure_(computer_programming)>).

## Selenium random errors

Selenium offers plenty of opportunities to shoot yourself in the foot: _race conditions_, _stale element_ errors, and so on.

The answer here is **pragmatic**: add `WebDriverException` directly to `transient_errors`, with a generous retry count (8, which means 9 lives, like a
cat 🐱).

Capture all Selenium errors and watch the retries in the logs.  
From there, it becomes easy to identify tests that could use some improvement.

## Discrete random errors

Even more surprising: applications displaying error toasts for no apparent reason, or forms reporting validation errors on perfectly correct inputs,
without actually blocking the flow.

These errors are the hardest to catch, precisely because they are _painless_. You can't simply notice a crash and add a _retry policy_ while waiting
for the bug to be fixed. They are, for all intents and purposes, invisible.

What's left? Butchering the test scenarios, or reaching for "ninja techniques."  
Ocarina refuses both.

Use _watchers_:

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

`catch_me_if_you_can_cb` is the _callback_ that the _watcher_ will invoke every 0.8 seconds (`poll_interval`).

Let's clarify a few things.

### Using Javascript

The _watcher_ is error-tolerant: it swallows exceptions silently.  
There is therefore no benefit to using a Selenium function to grab a page element, it would only add unnecessary baggage.  
Using Selenium's native functions would mean dealing with _implicit timeout_ concerns.

Going straight through _Javascript_ bypasses all internal _polling_ logic and keeps the _watcher_'s execution as non-blocking as possible for the test
running on the same _driver_.

The whole trick becomes invisible, as it only takes a few milliseconds.

### Fingerprinting

_Watchers_ expose a simple string cache, designed specifically for this need: if the same error stays visible and is detected every 0.8 seconds,
there's no point seeing it show up repeatedly in screenshots, reports, and logs. The fingerprint lets you ignore what you've already seen.

### Report

At the end of the _callback_, it calls: `watcher.report`.  
This call manages:

1. Logging the friction detected by the _watcher_,
2. Taking a screenshot as a trace of what was detected.

### HumanizedDriver

Nothing stops us from attaching behaviors to the _logger_ or the _driver_. Here, since the form is temperamental, we opt for a slow, "humanized" test:
typing with typos, corrections, hesitations. We simply wrap the _driver_ in a _proxy_, `HumanizedDriver`.

## Concurrency Heisenbugs

My quest was not over yet.  
I once watched colleagues count to three before all clicking at the same time to trigger the same action, right there in the office. I found myself
questioning the meaning of my life. And yet, by doing so, they genuinely managed to reproduce bugs.

This behavior can be reproduced with Ocarina.  
By default, Ocarina is aggressive.

Its `saturate_workers` option forces random test cloning within a suite.  
Whenever there are more _workers_ available in the _DriversPool_ than tests to run in a suite, Ocarina will randomly clone tests, spin up all drivers,
and assign each of them a test to execute.

This option can be enabled from the `bootstrap` function. It can also be toggled individually, either at the suite level or at the campaign level.  
When there is a conflict, the deepest element in the hierarchy has the final say.  
For instance, if a campaign disables the option but a suite enables it, the suite takes priority.

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

It is also possible to temporarily create a suite with a single test to maximize targeting precision.  
Or to run the cycle across multiple machines simultaneously (horizontal scaling).

Beyond concurrency concerns, this cloning mechanism also aims to ensure that passing tests owe nothing to chance. This effect is amplified by the
degree of horizontal scaling and the number of workers involved.

<llm-exclude>

---

![You reading Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Excellent work!<br/>See you soon, Mojo reader.</i></p>

---

<p align="center" class="inspiring-quote">"Retry flaky blocks."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Yegor Bugayenko, <i><a href="https://github.com/yegor256/prompt" target="_blank" rel="noreferrer">Prompt</a></i></p>

</llm-exclude>
