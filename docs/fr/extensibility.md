---
sticky: 1
description: Si l'on ne croit pas à la liberté d'expression pour les gens qu'on méprise, on n'y croit pas du tout.

date: 2026-04-30

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Extensibilité

## ValidationChain

Utilisable dans les POMs, `validate` permet d'exprimer des invariants sous forme de chaînes. L'exécution est **différée** : il faut appeler
`.execute()` explicitement.

Le résultat expose `is_valid`, `errors` et `validated_values`. Il est inerte par défaut. `.raise_if_invalid()` remonte l'exception si besoin.

```python
validate(checkbox.is_selected(), name="checkbox_is_selected").assert_that(
  is_truthy, msg="Couldn't select the OTP checkbox."
).execute().raise_if_invalid()
```

### Chaînage d'invariants

Plusieurs assertions sur une même valeur :

```python
validate(unsafe_min_date, name="cached_min_date")
.assert_that(is_str)
.assert_that(is_iso_utc_date_string).execute().raise_if_invalid()
```

### Chaînage de validations

Plusieurs validations sur des valeurs différentes :

```python
chain_validations(
    validate(unsafe_username, name="cached_username").assert_that(is_str),
    validate(unsafe_min_date, name="cached_min_date")
    .assert_that(is_str)
    .assert_that(is_iso_utc_date_string),
).execute().raise_if_invalid()
```

### Invariants réutilisables

Pour factoriser une validation récurrente, créer un _Invariant Validator_ :

```python
def _workers_amount_chain(
    chain: ValidationStartBlock[int],
    value: int,
) -> ValidationAssertBlock[int]:
    msg = f"Value Error: Number of workers must be at least 1 (got: {value})."
    return chain.assert_that(is_positive, msg=msg).assert_that(is_not_zero, msg=msg)


def validate_workers_amount(
    *, workers_amount: int, name: str
) -> ValidationAssertBlock[int]:
    """Validate that workers amount is at least 1."""
    return FrameworkInvariantValidator.create(
        workers_amount, name, _workers_amount_chain
    )

# * ...
validate_workers_amount(
    workers_amount=max_workers, name="max_workers"
).execute().raise_if_invalid()
```

Convention : `FrameworkInvariantValidator.create` pour les invariants techniques, `BusinessInvariantValidator.create` pour le métier.

### Assertions personnalisées

Sans argument :

```python
def is_str(value: Any) -> None:
    if not isinstance(value, str):
        msg = "Expected value to be string."
        raise InvariantViolationError(msg)
```

Avec argument :

```python
def is_equal_to(cmp: Any) -> Predicate[Any]:
    def unwrapped(value: Any) -> None:
        if value != cmp:
            msg = f"{value} is not equal to {cmp}."
            raise InvariantViolationError(msg)

    return unwrapped
```

### Type safety

Le _type checker_ détecte les assertions incompatibles avec le type de la valeur :

```python
validate("lol", name="n").assert_that(is_positive)

# error: Argument 1 to "assert_that" of "ValidationStartBlock" has incompatible type "Callable[[float], None]"; expected "Callable[[str], None]"
```

## Success et failure

`.success` et `.failure` prennent chacun un _effet_ à exécuter.  
[L'exemple canonique](https://github.com/mojo-molotov/ocarina-example) implémente plusieurs handlers : log simple d'erreur, log avec URL courante, log
de succès, et log de succès avec screenshot (+ URL).

```python
def _append_current_url_in_msg(msg: str, driver: WebDriver) -> str:
    try:
        driver_healthcheck(driver)
        extended_msg = f"{msg}\nCurrent URL: {driver.current_url}"
    except DriverDiedError:
        extended_msg = f"{msg}\nThe WebDriver is down, can't provide the current URL."

    return extended_msg


def create_just_log_error(*, logger: ILogger) -> Callable[[str], FailureHandler]:
    return lambda msg: lambda exc: logger.error(msg, exc=exc)


def create_log_error_with_current_url(
    *, logger: ILogger, driver: WebDriver
) -> Callable[[str], FailureHandler]:
    def unwrapped(msg: str) -> FailureHandler:
        def _log_error_with_url_effect(exc: Exception) -> None:
            extended_msg = _append_current_url_in_msg(msg, driver)
            return create_just_log_error(logger=logger)(extended_msg)(exc)

        return _log_error_with_url_effect

    return unwrapped


def create_just_log_success(*, logger: ILogger) -> Callable[[str], SuccHandler]:
    def unwrapped(msg: str) -> SuccHandler:
        def _log_effect() -> None:
            logger.success(msg)

        return _log_effect

    return unwrapped


def create_log_success_and_take_screenshot(
    *, logger: ILogger, driver: WebDriver
) -> Callable[[str], SuccHandler]:
    def unwrapped(msg: str) -> SuccHandler:
        def _log_and_take_screenshot_effect() -> None:
            performed_dependent_effect = create_just_log_success(logger=logger)(msg)()
            take_screenshot(driver=driver, logger=logger, category="SUCCESS")
            return performed_dependent_effect

        return _log_and_take_screenshot_effect

    return unwrapped


def create_log_success_with_current_url_and_take_screenshot(
    *, logger: ILogger, driver: WebDriver
) -> Callable[[str], SuccHandler]:
    def unwrapped(msg: str) -> SuccHandler:
        def _log_success_with_url_and_take_screenshot_effect() -> None:
            return create_log_success_and_take_screenshot(logger=logger, driver=driver)(
                _append_current_url_in_msg(msg, driver)
            )()

        return _log_success_with_url_and_take_screenshot_effect

    return unwrapped
```

D'autres _handlers_ sont envisageables :

- **`create_log_error_with_retry_hint`** : signale une _transient error_ et donc la possibilité de flakiness,
- **`create_log_error_and_send_alert`** : envoie un webhook à l'échec, sans polluer le test,
- **`create_log_success_and_record_timing`** : capture un timestamp de fin pour mesurer la durée d'un step (à combiner avec `on_run_effect` de
  `create_act`),
- Etc.

La création d'un _combinateur_ est également envisageable.

## Plugins

`bootstrap` permet de lancer des plugins post-exécution basés sur les résultats du cycle de test. Par exemple, `generate_docx_proof` parcourt
l'arborescence de logs et génère un document Word (preuve de test) par cas de test, en insérant les captures d'écran et en convertissant les dates UTC
en heure locale.

Le principe : les plugins réassemblent les artefacts générés en cours de route sous une forme différente. Un plugin pour créer un rapport sous forme
de tableau de bord web serait par exemple tout à fait envisageable.

## Grammaire extensible

La grammaire des scénarios de test repose sur un seul type : `ChainRunner[T]`. Un scénario est une `list[ChainRunner]` exécutée séquentiellement,
court-circuitée au premier échec. `drive_page` n'est qu'une fine enveloppe autour de `chain_actions`, qui construit un `ChainRunner`. N'importe quelle
fonction renvoyant un `ChainRunner` s'insère sans toucher au framework.

`match_page` a été ajouté après coup pour gérer les pages à état variable (banners optionnels, A/B tests, pages de maintenance...) : elle évalue des
conditions dans l'ordre et exécute la première branche correspondante.

Autre exemple envisageable : **`skip_if`**, qui court-circuiterait volontairement une portion du scénario sur une condition sans échouer (retournerait
un `Ok` neutre), utile pour des étapes optionnelles selon l'environnement ou les données de test.

**La seule contrainte du point d'extension : retourner un `ChainRunner`.**

<llm-exclude>

---

![Tu es un Mojo lecteur !](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Bon travail !<br/>À une prochaine fois, lecteur Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Le style, pour l'écrivain aussi bien que pour le peintre, est une question non de technique, mais de vision."</p>

<p align="right" class="inspiring-quote-author">― Marcel Proust</p>

</llm-exclude>
