---
sticky: 1
description: On ne voyage pas pour arriver, mais pour voyager.

date: 2026-04-26

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Premiers pas

## Avertissement

> **Note&nbsp;:**&nbsp;ce livre a pour but de faciliter la prise en main du projet `ocarina-example` fourni, qui reste **la source de vérité** à
> consulter en toutes circonstances.

> ⚠️&nbsp;Le livre sacré d'Ocarina N'EST PAS et ne sera jamais "clé en main". Ocarina demande une certaine maturité pour être utilisé. Par conséquent,
> nous ne nous focaliserons que sur ce qui peut réellement être piégeux.

Cette page explique le chemin avant toute chose. De la pratique sera nécessaire dans tous les cas.  
[📖 Munissez-vous de l'exemple canonique comme référence.](https://github.com/mojo-molotov/ocarina-example)

## 1. Mise en place du projet

Créez un nouveau projet Python, puis installez les dépendances nécessaires&nbsp;:

```bash
pip install selenium
pip install ocarina
```

Ensuite, créez votre structure de dossiers.

## 2. Les adapters

Ocarina repose sur un système d'_adapters_ que l'utilisateur a la responsabilité d'écrire. Ils permettent de configurer le framework selon les
contraintes et conventions propres à chaque projet.

Les _adapters_ principaux à créer sont les suivants&nbsp;:

- `act` _(requis)_
- `test_campaign` _(requis)_
- `test_suite` _(requis)_
- `env_getters` _(facultatif)_
- `match_page` _(facultatif)_

### 2.1 EnvGetters

L'`EnvGetters` d'Ocarina centralise et type l'accès aux variables d'environnement. Il se divise en deux catégories&nbsp;:

- **Creds**&nbsp;:&nbsp;paires login/mot de passe, exprimées sous forme de dictionnaires immutables.
- **Values**&nbsp;:&nbsp;valeurs individuelles (chaînes de caractères).

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

Une fois cet _adapter_ en place, il devient possible de récupérer une valeur ou des credentials de la façon suivante&nbsp;:

```python
redis_url = create_env_getters().get_value("xxxxx_url")
dashboard_creds = create_env_getters().get_credentials("dashboard")
print(redis_url)
print(dashboard_creds["login"])
print(dashboard_creds["password"])
```

> **Note&nbsp;:**&nbsp;les clés valides sont à fournir à travers deux types tel que&nbsp;:&nbsp;`EnvGetters[_CredsKeys, _ValuesKeys]`. Dans le cas où
> l'utilisateur ne souhaite utiliser QUE la fonctionnalité `.get_value()`, il suffit de typer `_CredsKeys` tel que&nbsp;:&nbsp;`Never`. Il en va de
> même pour `_ValuesKeys` à typer en tant que `Never` si l'utilisateur ne souhaite utiliser QUE la fonctionnalité `.get_credentials()`.

Nos accesseurs sont alors strictement typés, par exemple&nbsp;:

```python
redis_url = create_env_getters().get_value("x")

# error: Argument 1 to "get_value" of "EnvGetters" has incompatible type "Literal['x']"; expected "Literal['igor_xxx_key', 'xxxxx_url']"
```

### 2.2 Act

Dans Ocarina, `act` est le verbe utilisé pour exprimer un pas de test au sein d'un scénario. Sa construction est intentionnellement laissée à la
charge de l'utilisateur, pour des raisons abordées plus loin dans ce livre (_hooks_).

Sa forme minimale est la suivante&nbsp;:

```python
def act(pom: TPOM, action: Callable[[TPOM], TPOM]) -> ActionStart[TPOM]:
    """Act on a page."""

    return create_act(
        pom,
        action,
    )
```

### 2.3 TestCampaign

L'_adapter_ `TestCampaign` est volontairement minimaliste. La seule information qu'Ocarina ne peut pas deviner est le **nombre de workers**,
c'est-à-dire le nombre de navigateurs à faire tourner en parallèle pour une campagne. Ce paramètre pouvant aussi être passé directement via la CLI, un
petit _adapter_ suffit&nbsp;:

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

> Le type du `WebDriver` utilisé (Selenium ou autre) est injecté ici&nbsp;:&nbsp;`OriginalTestCampaign[WebDriver]`.  
> Et ici&nbsp;:&nbsp;`suites: Sequence[TestSuite[WebDriver]]`

> ✅ Bien évidemment, insérez VOTRE `TestSuite` adaptée ici, pas la _built-in_ d'Ocarina.

### 2.4 TestSuite

C'est l'_adapter_ le plus important à comprendre. `TestSuite` expose nativement un grand nombre de paramètres. L'objectif de cet _adapter_ est de
créer une **façade**&nbsp;:&nbsp;certaines valeurs sont figées une bonne fois pour toutes (_hard-codées_), d'autres sont exposées optionnellement avec
des valeurs par défaut. C'est un _rétrécissement_.

Par exemple&nbsp;:

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

> Le type du `WebDriver` utilisé (Selenium ou autre) est injecté ici&nbsp;:&nbsp;`OriginalTestSuite[WebDriver]`.  
> Ainsi qu'ici&nbsp;:&nbsp;`tests: Sequence[Test[WebDriver]]`  
> Et ici&nbsp;:&nbsp;`drivers_pool: SeleniumWebDriversPool`

#### Transient errors

La notion de `transient_errors` est centrale dans `TestSuite`.  
Ces erreurs sont traitées comme du **bruit**&nbsp;:&nbsp;si un test échoue à cause d'une exception listée dans `transient_errors`, il est
automatiquement rejoué.  
Le nombre maximum de tentatives est défini par `max_retries_per_test`.

Ce mécanisme rend l'exécution des tests tolérante à la _flakiness_. Les tests qui rejouent fréquemment apparaissent clairement dans les logs, ce qui
permet aux mainteneurs d'identifier et corriger les sources d'instabilité, qu'elles soient liées à une mauvaise utilisation de Selenium, à des
conditions d'environnement hors de portée, ou à d'autres facteurs externes.

#### Only IDs et exclude IDs

Ces deux paramètres permettent l'exécution conditionnelle de tests.  
Ce sont des filtres par ID.

> ⚠️&nbsp;**Attention à bien les inclure dans cet _adapter_, sinon ces valeurs passées depuis la CLI ne seront pas prises en compte.**

### 2.5 MatchPage

`match_page` est un opérateur d'Ocarina conçu pour gérer les pages à rendu non déterministe&nbsp;:&nbsp;bannières de cookies, challenges anti-bot, A/B
tests, etc.

Son fonctionnement repose sur un principe simple&nbsp;:&nbsp;**toute exception levée est interprétée comme un non-match, et donc avalée par
`match_page`**. Il est cependant possible d'exclure certaines exceptions de cette mécanique, afin qu'elles remontent normalement dans le flot
d'exécution.

Par souci de cohérence, on souhaite généralement que les `transient_errors` soient dans ce cas&nbsp;:&nbsp;elles doivent remonter plutôt qu'être
silencieusement avalées.

L'_adapter_ se crée tel que&nbsp;:

```python
match_page = create_match_page(raised_exceptions=transient_errors)
```

## 3. Écrire un premier POM

Le pattern POM (_Page Object Model_) étant un standard bien établi, nous n'en reprenons pas la définition ici.

Voici comment créer son premier POM avec Ocarina&nbsp;:

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

Quelques points méritent d'être détaillés.

### 3.1 SeleniumTitleMixin

Tout objet héritant de `POMBase` doit implémenter une méthode `get_current_title`. `SeleniumTitleMixin` fournit cette implémentation de façon
transparente, sans qu'il soit nécessaire de l'écrire manuellement.

Son rôle ne s'arrête pas là&nbsp;:&nbsp;il définit également l'attribut `_driver` avec le type `WebDriver` (Selenium), ce qui le rend **incompatible
avec tout autre type**. Tenter d'y assigner une valeur incorrecte produira immédiatement une erreur de typage&nbsp;:

```python
self._driver = "lol"

# error: Incompatible types in assignment (expression has type "str", variable has type "WebDriver")
```

`SeleniumTitleMixin` joue donc aussi un rôle de **détrompeur de typage**. Des mixins analogues existent ou peuvent être créés pour d'autres
technologies d'automatisation de navigateur.

### 3.2 Retourner `self`

Chaque méthode d'action retourne `self`. C'est un choix de design volontaire dans Ocarina, à respecter systématiquement, il permet le chaînage des
appels et la composition fluide des scénarios.

## 4. Écrire des connectors

Les connectors sont une couche fine mais indispensable pour la lisibilité des scénarios. Ils encapsulent les appels aux méthodes du POM derrière des
fonctions nommées explicitement&nbsp;:

```python
def open_homepage(p: Homepage) -> Homepage:
    """Open my homepage."""
    return p.open()


def verify_homepage(p: Homepage) -> Homepage:
    """Verify we are on my homepage."""
    return p.verify()
```

Il est également possible de les composer directement&nbsp;:

```python
def open_then_verify_homepage(p: Homepage) -> Homepage:
    """Open my homepage, then verify it."""
    return p.open().verify()
```

## 5. Écrire un premier scénario

Les briques sont en place.  
Voici comment les assembler en scénario&nbsp;:

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

Chaque pas de test est exprimé via `act`, auquel on chaîne un handler `.failure()` et un handler `.success()`.  
Le scénario est ensuite encapsulé dans un objet `Test` via `create_selenium_test`.

## 6. Créer une suite de test

Une suite regroupe un ensemble de tests à exécuter sur une même _pool_ de drivers&nbsp;:

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

## 7. Créer une campagne de test

Une campagne regroupe plusieurs suites&nbsp;:

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

## 8. Créer un cycle de test

Un cycle regroupe plusieurs campagnes. C'est l'unité d'exécution de plus haut niveau&nbsp;:

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

## 9. Bootstrapper le projet

Voici le point d'entrée complet du projet&nbsp;:

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

Le déroulement est le suivant&nbsp;:

1. Les arguments récupérés via la CLI sont poussés dans un store global.
2. Une _pool_ de drivers est créée, c'est celle-ci qui gère le cycle de vie des navigateurs web en parallèle.
3. Une callback `_post_exec` est définie&nbsp;:&nbsp;elle s'exécute après les tests et les plugins, affiche les résultats, et retourne un code
   d'erreur si le cycle a échoué.
4. L'ensemble est bootstrappé à l'intérieur d'un chronomètre mesurant la durée totale d'exécution. Le flot d'exécution est
   donc&nbsp;:&nbsp;**cycle&nbsp;→&nbsp;plugins&nbsp;→&nbsp;post_exec**.

> ℹ️ Les plugins sont des fonctions déférées passées à `run_plugins`.  
> `run_plugins` prend `results` en argument,  
> ce qui indique sans ambiguïté par simple lecture de signature de fonction qu'ils s'exécutent en post-traitement, une fois les résultats disponibles.

<llm-exclude>

---

![Tu es un Mojo lecteur !](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Bon travail&nbsp;!<br/>À une prochaine fois, lecteur Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Pour l'instant, vivez les questions. Peut être, un jour lointain, entrerez-vous ainsi, peu à peu, sans l'avoir remarqué, à l'intérieur de la réponse."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Rainer Maria Rilke</p>

</llm-exclude>
