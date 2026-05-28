---
sticky: 1
description: It's not about the destination, it's about the journey.

date: 2026-04-26

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# First steps

## Disclaimer

> **Note:** this book is intended to help you get familiar with the provided `ocarina-example` project, which remains **the source of truth** to refer
> to in all circumstances.

> ⚠️ _The Ocarina Holy Book_ is NOT and will never be "plug-and-play." Ocarina requires a good level of maturity to use. As such, we will only focus
> on what can genuinely be tricky.

This page explains the _journey_. After that, practice will be necessary.  
[📖 Get the canonical example as a reference.](https://github.com/mojo-molotov/ocarina-example)

## 1. Project setup

Create a new Python project, then install the required dependencies:

```bash
pip install selenium
pip install ocarina
```

Then create your folder structure.

## 2. Adapters

Ocarina is built around a system of adapters that the user is responsible for writing. They allow the framework to be configured according to the
constraints and conventions of each project.

The main adapters to create are:

- `act` _(required)_
- `test_campaign` _(required)_
- `test_suite` _(required)_
- `env_getters` _(optional)_
- `match_page` _(optional)_

### 2.1 EnvGetters

Ocarina's `EnvGetters` centralizes and types access to environment variables. It is divided into two categories:

- **Creds**: login/password pairs, expressed as immutable dictionaries.
- **Values**: individual values (strings).

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

Once this adapter is in place, retrieving a value or credentials looks like this:

```python
xxxxx_url = create_env_getters().get_value("xxxxx_url")
dashboard_creds = create_env_getters().get_credentials("dashboard")
print(xxxxx_url)
print(dashboard_creds["login"])
print(dashboard_creds["password"])
```

> **Note:** valid keys are provided through two types: `EnvGetters[_CredsKeys, _ValuesKeys]`. If the user only wants to use `.get_value()`, it is
> enough to type `_CredsKeys` as `Never`. The same applies to `_ValuesKeys`, which should be typed as `Never` if the user only wants to use
> `.get_credentials()`.

Our accessors are then strictly typed. For example:

```python
xxxxx_url = create_env_getters().get_value("x")

# error: Argument 1 to "get_value" of "EnvGetters" has incompatible type "Literal['x']"; expected "Literal['igor_xxx_key', 'xxxxx_url']"
```

### 2.2 Act

In Ocarina, `act` is the verb used to express each single step in a test scenario. Its construction is intentionally left to the user, for reasons
covered later in this book (_hooks_).

Its minimal shape is as follows:

```python
def act(pom: TPOM, action: Callable[[TPOM], TPOM]) -> ActionStart[TPOM]:
    """Act on a page."""

    return create_act(
        pom,
        action,
    )
```

### 2.3 TestCampaign

The `TestCampaign` adapter is intentionally minimal. The only piece of information Ocarina cannot infer is the **number of workers**, i.e. the number
of browsers to run in parallel for a given campaign. Since this parameter can also be passed directly via the CLI, a small adapter is all that is
needed:

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

> The `WebDriver` type (Selenium or otherwise) is injected here: `OriginalTestCampaign[WebDriver]`.  
> And here: `suites: Sequence[TestSuite[WebDriver]]`

> ✅ Of course, insert YOUR adapted `TestSuite` here, not Ocarina's built-in one.

### 2.4 TestSuite

This is the most important adapter to understand. `TestSuite` natively exposes a large number of parameters. The goal of this adapter is to create a
**facade** around it: some values are hardcoded once and for all, others are optionally exposed with sensible defaults. _Narrowing_.

Likewise:

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

> The `WebDriver` type (Selenium or otherwise) is injected here: `OriginalTestSuite[WebDriver]`.  
> Also here: `tests: Sequence[Test[WebDriver]]`  
> And here: `drivers_pool: SeleniumWebDriversPool`

#### Transient errors

The concept of `transient_errors` is central to `TestSuite`.  
These errors are treated as **noise**: if a test fails due to an exception listed in `transient_errors`, it is automatically replayed.  
The maximum number of attempts is defined by `max_retries_per_test`.

This mechanism makes test execution tolerant to _flakiness_. Tests that replay frequently appear clearly in the logs, allowing maintainers to identify
and fix sources of instability, whether caused by improper use of Selenium, out-of-scope environment conditions, or other external factors.

#### Only IDs and exclude IDs

These two parameters enable conditional test execution.  
They are ID-based filters.

> ⚠️ **Make sure to include them in this adapter, otherwise those CLI flags will not be handled.**

### 2.5 MatchPage

`match_page` is an Ocarina operator designed to handle pages with non-deterministic rendering: cookie banners, anti-bot challenges, A/B tests, etc.

Its logic is straightforward: **any exception raised is interpreted as a non-match, and therefore swallowed by `match_page`**. It is however possible
to exclude some exceptions from this mechanism, so that they propagate normally up the execution flow.

For consistency, `transient_errors` should generally fall into this category: they must propagate rather than be silently swallowed.

The adapter is created as follows:

```python
match_page = create_match_page(raised_exceptions=transient_errors)
```

## 3. Writing a first POM

The POM (_Page Object Model_) pattern is a well-established standard, so we won't redefine it here.

Here is how to create a first POM with Ocarina:

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

A few points are worth detailing.

### 3.1 SeleniumTitleMixin

Any object inheriting from `POMBase` must implement a `get_current_title` method. `SeleniumTitleMixin` provides this implementation transparently,
without requiring it to be written manually.

Its role goes further: it also defines the `_driver` attribute with the `WebDriver` type (Selenium), making it **incompatible with any other type**.
Attempting to assign an incorrect value will immediately produce a type error:

```python
self._driver = "lol"

# error: Incompatible types in assignment (expression has type "str", variable has type "WebDriver")
```

`SeleniumTitleMixin` therefore also acts as a **type guard**. Analogous mixins can be created for other browser automation technologies.

### 3.2 Returning `self`

Every action method returns `self`. This is a deliberate design choice in Ocarina, to be followed consistently: it enables method chaining and fluent
scenario composition.

## 4. Writing connectors

Connectors are a thin but essential layer for scenario readability. They wrap POM method calls behind explicitly named functions:

```python
def open_homepage(p: Homepage) -> Homepage:
    """Open my homepage."""
    return p.open()


def verify_homepage(p: Homepage) -> Homepage:
    """Verify we are on my homepage."""
    return p.verify()
```

They can also be composed directly:

```python
def open_then_verify_homepage(p: Homepage) -> Homepage:
    """Open my homepage, then verify it."""
    return p.open().verify()
```

## 5. Writing a first test scenario

All the building blocks are in place.  
Here is how to assemble them into a scenario:

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

Each test step is expressed via `act`, to which a `.failure()` and a `.success()` handler are chained.  
The scenario is then wrapped in a `Test` object via `create_selenium_test`.

## 6. Creating a test suite

A suite groups a set of tests to be executed against the same driver pool:

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

## 7. Creating a test campaign

A campaign groups multiple suites:

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

## 8. Creating a test cycle

A cycle groups multiple campaigns. It is the highest-level execution unit:

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

## 9. Bootstrapping the project

Here is the complete entry point for the project:

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

The flow is as follows:

1. Arguments retrieved from the CLI are pushed into a global store.
2. A driver pool is created: it manages the lifecycle of web browsers running in parallel.
3. A `_post_exec` callback is defined: it runs after tests and plugins, prints the results, and exits with an error code if the cycle has failed.
4. Everything is bootstrapped inside a timer measuring the total execution duration. The execution flow is therefore:
   **cycle&nbsp;→&nbsp;plugins&nbsp;→&nbsp;post_exec**.

> ℹ️ Plugins are deferred functions passed to `run_plugins`.  
> `run_plugins` takes `results` as an argument,  
> which makes it immediately clear from the function signature alone that they run as post-processing, once results are available.

<llm-exclude>

---

![You reading Mojo!](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Excellent work!<br/>See you soon, Mojo reader.</i></p>

---

<p align="center" class="inspiring-quote">"Live the questions now. Perhaps then, someday far in the future, you will gradually, without even noticing it, live your way into the answer."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Rainer Maria Rilke</p>

</llm-exclude>
