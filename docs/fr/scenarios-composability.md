---
sticky: 1
description:
  La langue n'est ni réactionnaire, ni progressiste. Elle est tout simplement fasciste, car le fascisme, ce n'est pas d'empêcher de dire, c'est
  d'obliger à dire.

date: 2026-04-27

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Premiers scénarios

## La fin des états invalides

_... Rendre les états invalides impossibles à représenter._

Nous allons détailler le fonctionnement d'`act`, de `drive_page` et de `match_page` dans l'écriture des scénarios de test avec Ocarina.

### Act et drive_page

#### Exemple canonique

Commençons par un exemple que nous allons progressivement casser :

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

`drive_page` exprime que l'on prend le contrôle d'_une_ page.  
Toute _transition_ devient explicite par l'ouverture d'un nouveau `drive_page`.  
À l'intérieur, `act` exprime une action émise sur cette page : c'est un _pas de test_. `drive_page` est variadique, elle accepte autant de `act` que
nécessaire, et la virgule entre chacun devient un ET :

> Ouvre, puis vérifie la page d'accueil. _ET_ clique sur le CTA. On change de page : vérifie que l'on est sur la page pour réserver un appel.

#### Système immunitaire

Essayons d'appeler `verify_book_call_page` sur `homepage` :

```python
act(on_homepage, verify_book_call_page)

# error: Argument 2 to "act" has incompatible type "Callable[[BookCallPage], BookCallPage]"; expected "Callable[[Homepage], Homepage]"
```

L'action est incompatible avec sa cible. Ce programme ne _compile_ pas.

Oublions un `.success` :

```python
drive_page(
    act(on_book_a_call_page, verify_book_call_page)
    .failure(just_log_error("Failed to verify the 'Book a call' page..."))
)

# error: Expected type 'ActionSuccess[TPOM ≤: POMBase]', got 'ActionFailure[BookCallPage]' instead
```

Plaçons un `.success` immédiatement après `act` :

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

Inversons `.success` et `.failure` :

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

Chaînons des `act` hétérogènes dans un même `drive_page` :

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

AUCUNE de ces fantaisies ne compile. Ocarina est anti _petit malin_.

Beaucoup se battent avec des _coding styles_.  
Ocarina est plus tranché : si le style n'est pas respecté, ce n'est pas une erreur de _lint_, ce n'est pas un avertissement. Ça ne **compile** pas.

Ocarina force le même gabarit pour tout le monde, et ces erreurs apparaissent directement dans l'éditeur via _mypy_ : feedback instantané.

<llm-exclude>

L'objectif est de clore les débats de _geeks_ au plus tôt. C'est ainsi qu'Ocarina enverra directement sur
[r/AntiTaff](https://www.reddit.com/r/AntiTaff/) tous les slipologues du monde.&nbsp;✈️

</llm-exclude>

**La priorité des scénarios de test est leur uniformité et leur simplicité. C'est tout.**

### match_page

`match_page` gère les situations où une page peut être rendue de manière différente.

Commençons par le principe des _matchers_ :

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

**Un _matcher_ vérifie de manière minimale si quelque chose est vrai, en allant au plus vite.**

---

> ⚠️ Il vaut mieux éviter un `.find_element(s)` brut : c'est la voie rapide vers la _flakiness_.

Le délai maximal de 5 secondes n'aura aucun impact dans une batterie scalée horizontalement, ce n'est donc pas une pratique à craindre ici. Il n'est
pas non plus recommandé de déguiser un `verify` en _matcher_ : **ce sont deux outils différents.**

---

Usage dans un scénario :

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

`match_page` se pose au même niveau que `drive_page` et est chaînable. Sa commande `then` attend à nouveau une chaîne de `drive_page` ou `match_page`.
Les branches sont définies par `when`.

`match_page` et `when` ont été ajoutés après coup, l'Igoristan était tellement aléatoire que le cas d'usage s'est imposé de lui-même.  
Leur implémentation a été simple, preuve de la flexibilité de la grammaire : d'autres structures analogues pourraient très bien suivre.

## Répétitions

Pour répéter une chaîne de test (par exemple, pour tester plusieurs tentatives d'accès non autorisé), il suffit de multiplier la liste :

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

Un _fragment_ est une fonction `(driver, logger) -> TestChain` injectable avant ou après la chaîne principale, via `pre_test_scenarios_fragments` et
`post_test_scenarios_fragments`.

Par exemple, `login_without_otp_happy_path` est un fragment :

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

Injection au début :

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

Injection à la fin :

```python
test_dashboard_login_page_back_to_igoristan_button = create_selenium_test(
    name="Use the go back to Igoristan button",
    test_scenario=lambda driver, logger: Scenario(
        test_chain=just_go_back_to_igoristan(driver, logger)
    ),
    post_test_scenarios_fragments=[verify_homepage],  # <- [!]
)
```

Les deux paramètres peuvent être combinés et acceptent chacun une liste de _fragments_, injectés dans l'ordre fourni.

## Aliasing

Les scénarios peuvent devenir lourds.  
Comme tout y est déclaratif, l'utilisateur est libre de créer des alias :

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

Toute valeur peut être aliasée et réutilisée.  
Cette écriture est pure, elle ne provoque aucun _effet_ immédiat.  
Tout peut être redéclaré ailleurs, réorganisé ailleurs, tant que la chaîne finale correspond à l'attendu.

<llm-exclude>

---

![Tu es un Mojo lecteur !](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Bon travail !<br/>À une prochaine fois, lecteur Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"La perfection est atteinte non pas lorsqu'il n'y a plus rien à ajouter, mais lorsqu'il n'y a plus rien à retirer."</p>

<p align="right" class="inspiring-quote-author">― Antoine de Saint-Exupéry</p>

</llm-exclude>
