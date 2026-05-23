---
sticky: 1
description: And under ice, a river glitters...

date: 2026-04-28

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# First jutsus

## Datasets

Driving a test with a dataset is straightforward with Ocarina:

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

A [_closure_](<https://en.wikipedia.org/wiki/Closure_(computer_programming)>) is all it takes.  
Note that `Scenario` is declared from the inside here. It makes sense, since the whole point is to encapsulate it.

`multi_login_tests` is therefore a _list_ of `Test`, which we _unpack_ into a `TestSuite`, like so:

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

## Smoke tests

<llm-exclude>

> 📖 A smoke test is a quick, shallow verification of a software system to ensure its core functions work correctly, before running deeper tests. The
> goal is to catch obvious blocking failures early: if things go up in smoke right away, there's no point going further.

</llm-exclude>

To run smoke tests at the start of a cycle with Ocarina:

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

`mode` accepts two values (default: `"fail-fast-on-first-smoke-campaigns-sequence-fail"`):

- `"fail-fast-on-first-smoke-campaigns-sequence-fail"`: as soon as one smoke-test campaign fails, the remaining ones are skipped.
- `"wait-for-all-smoke-tests"`: all smoke-test campaigns run to completion, even if one fails along the way.

In both cases, main tests are skipped if any smoke test has failed.

## Setup and teardown

`Scenario` accepts two optional callbacks: `setup` and `teardown`.

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

### Lifecycle

1. `setup()`: runs before the `test_chain`. On failure, the `test_chain` is skipped and `teardown` still runs. If every attempt fails due to setup,
   the test is marked **SKIPPED** (not **FAILED**),
2. `test_chain`: the actual test steps,
3. `teardown()`: always runs, even on failure. Errors are logged and ignored.

`setup` and `teardown` are `Effect`.  
They are meant for infrastructure concerns: seeding a database, calling an API, cleaning up state...

If encapsulation is needed: _closure_.

## Proxy pattern

One use case from [the canonical example](https://github.com/mojo-molotov/ocarina-example) is `HumanizedDriver`:

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

The idea: return _Web Elements_ that behave differently for user-like interactions. Keystrokes, in this case.  
Transparent to the _type system_, transparent to the _runtime_.

Which then allows:

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

Or, with a _closure_:

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

The same principle applies to the logger, routing it toward a _sink_, for instance. That case isn't canonically covered by Ocarina.

## Reactive programming: NO

Ocarina test scenarios are intentionally static.  
Yet a web application is dynamic, and sometimes capturing a value on the fly to pass it to a later step is perfectly legitimate.

Ocarina doesn't answer that. It doesn't need to.

### Architectural answer

What we're after here is an _in-memory cache_.

We generate keys just before the test chain kicks off, and pass them to the POM actions. Actions write and read through a unique key.  
The scenario just hands them out:

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

## API calls and locks

API and locks have to be handled in the POMs.

> ⚠️ Ocarina doesn't support `async`/`await` and never will.

**API calls**: synchronous `requests` is enough.  
**Locks**: `threading.Lock` if a single process at a time, otherwise Redis distributed locks are enough (`redis.StrictRedis` + `redis.lock`).

## Browser profile

Some cases require passing a profile with `--profile-path`:

- **Proxy authentication**,
- **Pre-loaded extensions**,
- **Local settings** (language, timezone, certificates...),
- Etc.

<llm-exclude>

---

![You reading Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Excellent work!<br/>See you soon, Mojo reader.</i></p>

---

<p align="center" class="inspiring-quote">"Muddy water is best cleared by leaving it alone."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Alan Watts</p>

</llm-exclude>
