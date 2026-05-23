---
sticky: 1
description: Vois, sous la glace, le ruisseau brille...

date: 2026-04-28

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Premiers jutsus

## Jeux de données

Piloter un test grâce à un jeu de données est très simple avec Ocarina&nbsp;:

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

Une [_closure_](<https://fr.wikipedia.org/wiki/Fermeture_(informatique)>) suffit.  
On notera que `Scenario` est déclaré depuis l'intérieur ici&nbsp;:&nbsp;logique, puisqu'il s'agit de l'encapsuler.

`multi_login_tests` est donc une _liste_ de `Test`, que l'on _unpack_ dans une `TestSuite`, tel que&nbsp;:

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

## Tests de fumée

<llm-exclude>

> 📖 Un test de fumée (_smoke test_) est une vérification rapide et superficielle d'un logiciel ou d'un système pour s'assurer que ses fonctions de
> base fonctionnent correctement, avant de lancer des tests plus approfondis. L'objectif est de détecter rapidement les défauts bloquants
> évidents&nbsp;:&nbsp; si ça "prend feu" dès le départ, inutile d'aller plus loin.

</llm-exclude>

Pour lancer des tests de fumée en début de cycle avec Ocarina&nbsp;:

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

`mode` accepte deux valeurs (par défaut, `"fail-fast-on-first-smoke-campaigns-sequence-fail"`)&nbsp;:

- `"fail-fast-on-first-smoke-campaigns-sequence-fail"`&nbsp;:&nbsp;dès qu'une campagne de tests de fumée échoue, les suivantes sont passées (_skip_).
- `"wait-for-all-smoke-tests"`&nbsp;:&nbsp;toutes les campagnes de tests de fumée s'exécutent, même en cas d'échec intermédiaire.

Dans les deux cas, les tests principaux sont ignorés si au moins un test de fumée a échoué.

## Setup et teardown

`Scenario` accepte deux _callbacks_ optionnelles : `setup` et `teardown`.

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

### Cycle de vie

1. `setup()`&nbsp;:&nbsp;exécuté avant la `test_chain`. En cas d'échec, la `test_chain` est ignorée et le `teardown` s'exécute quand même. Si toutes
   les tentatives échouent à cause du setup, le test est marqué **SKIPPED** (pas **FAILED**),
2. `test_chain`&nbsp;:&nbsp;les étapes du test,
3. `teardown()`&nbsp;:&nbsp;toujours exécuté, même en cas d'échec. Les erreurs sont loggées et ignorées.

`setup` et `teardown` sont des `Effect`.  
Elles sont destinées aux préoccupations d'infrastructure : seeder une base de données, appeler une API, nettoyer un état...

Si une encapsulation est nécessaire&nbsp;:&nbsp;_closure_.

## Proxy pattern

Un cas d'usage de [l'exemple canonique](https://github.com/mojo-molotov/ocarina-example) est `HumanizedDriver`&nbsp;:

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

Le principe est de retourner des _Web Elements_ qui intègrent des comportements utilisateurs à l'interaction&nbsp;:&nbsp;les frappes clavier, en
l'occurrence.  
Transparent pour le _système de types_, transparent pour le _runtime_.

On peut alors faire&nbsp;:

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

Ou, avec une _closure_&nbsp;:

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

Le même principe s'applique au logger, pour le router vers un _sink_, par exemple, bien que ce cas ne soit pas couvert canoniquement par Ocarina.

## Programmation réactive&nbsp;:&nbsp;NON

Les scénarios de test d'Ocarina sont volontairement statiques.  
Pourtant, une application web est dynamique et parfois, enregistrer une valeur à la volée pour la passer à une étape suivante est tout à fait
légitime.

Ocarina n'y répond pas. Il n'en a pas besoin.

### Réponse architecturale

Ce qu'on cherche ici est un _cache in-memory_.

On génère des clés juste avant le lancement de la chaîne de test, et on les passe aux actions du POM. Les actions enregistrent et consomment via une
clé unique.  
Le scénario se contente de les fournir&nbsp;:

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

## Appels API et verrous

Les appels API et les verrous sont à gérer dans les POMs.

> ⚠️&nbsp;Ocarina ne supporte pas `async`/`await` et ne le fera pas.

**Appels API**&nbsp;:&nbsp;`requests` (synchrone) suffit.  
**Verrous**&nbsp;:&nbsp;`threading.Lock` si un seul process à la fois, sinon verrous distribués Redis (`redis.StrictRedis`&nbsp;+&nbsp;`redis.lock`).

## Profil navigateur

Certains cas nécessitent de passer un profil via `--profile-path`&nbsp;:

- **Authentification proxy**,
- **Extensions préchargées**,
- **Paramètres locaux** (langue, timezone, certificats...),
- Etc.

<llm-exclude>

---

![Tu es un Mojo lecteur !](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Bon travail&nbsp;!<br/>À une prochaine fois, lecteur Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"La meilleure façon de résoudre un problème est souvent d'en sortir."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Alan Watts</p>

</llm-exclude>
