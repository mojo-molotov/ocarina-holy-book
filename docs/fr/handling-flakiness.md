---
sticky: 1
description: La seule attitude judicieuse consiste à s'accommoder de l'état des choses.

date: 2026-04-29

head:
  - - meta
    - property: og:image
      content: https://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-reading.png
---

# Premiers obstacles du monde réel

<llm-exclude>
Cher ami, bienvenue.
</llm-exclude>

## Aléas serveur

Les erreurs serveur aléatoires sont coriaces.  
Durant une expérience de travail particulièrement pénible, j'ai eu à faire face à un environnement qui affichait régulièrement des pages d'erreur 500
totalement aléatoires, quelle que soit la zone explorée de l'application.

Dans ce genre de cas, Ocarina propose une réponse directement à la création du verbe `act`&nbsp;:

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

Le hook `on_failure` a précisément été conçu pour ça.  
Il suffit de créer des _guards_ et de modifier l'erreur encapsulée dans `Fail` pour provoquer un _rejeu_ du test ayant échoué en raison d'une cause
externe.

L'étape suivante devrait paraître familière&nbsp;:

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

Enfin, si `match_page` est également utilisé dans le projet et qu'une variable partagée `transient_errors` n'est pas souhaitée, il ne faudra pas
oublier d'ajouter ces nouvelles définitions d'erreurs aléatoires dans le `raised_exceptions` du constructeur de `match_page`.

Les logs des tests automatisés permettront d'amorcer une première conversation autour de ces problèmes.

## Aléas de pas de test

Pensant avoir laissé derrière moi ce genre de désagréments, j'ai changé de crémerie... pour y découvrir des formulaires instables et des systèmes
d'authentification qui fonctionnaient une fois sur deux.

Face à cela, la réponse d'Ocarina est différente&nbsp;:&nbsp;on délègue la responsabilité au POM.

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

Cela soulève aussi une question sur les _connectors_&nbsp;:&nbsp;comment leur ajouter des paramètres&nbsp;?

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

Il suffit de retourner le `def` avec la signature attendue, à l'intérieur d'une fonction qui capture les paramètres.  
C'est une [_closure_](<https://fr.wikipedia.org/wiki/Fermeture_(informatique)>).

## Aléas de Selenium

Selenium offre de nombreuses occasions de se tirer une balle dans le pied&nbsp;:&nbsp;_race conditions_, erreurs de "_stale element_", etc.

La réponse ici est **pragmatique**&nbsp;:&nbsp;ajouter `WebDriverException` directement aux `transient_errors`, avec un nombre de rejeux généreux (8,
soit 9 vies, comme un chat 🐱).

On capture toutes les erreurs Selenium et on observe les rejeux dans les logs.  
De là, il devient possible d'identifier les tests qui mériteraient d'être améliorés.

## Erreurs aléatoires discrètes

Plus surprenant encore&nbsp;:&nbsp;des applications affichant des toasts d'erreur sans raison apparente, ou des formulaires signalant des erreurs de
validation sur des saisies pourtant correctes, sans pour autant bloquer le parcours.

Ces erreurs sont les plus pénibles à détecter, car elles sont _indolores_. On ne peut pas simplement constater un crash et ajouter une _politique de
retry_ en attendant que l'anomalie soit corrigée. Elles sont, pour ainsi dire, invisibles.

Il resterait à massacrer les scénarios de test ou à recourir à des "techniques de ninjas".  
Ocarina refuse ces deux options.

La solution, les _watchers_&nbsp;:

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

`catch_me_if_you_can_cb` est la _callback_ que le _watcher_ appellera toutes les 0.8 secondes (`poll_interval`).

Détaillons un peu plus l'approche.

### Utilisation de Javascript

Le _watcher_ est tolérant aux erreurs&nbsp;:&nbsp;il les avale silencieusement.  
Il n'y a donc aucun intérêt à utiliser une fonction Selenium pour capturer un élément de la page, si ce n'est s'encombrer.  
Utiliser les fonctions natives de Selenium imposerait de gérer des questions d'_implicit timeout_.

Passer directement par du _Javascript_ permet de contourner toute logique de _polling_ interne et de rendre l'exécution du _watcher_ la moins
bloquante possible pour le test qui tourne sur le même _driver_.

Ce tour de passe-passe devient alors invisible, puisqu'il n'est que d'une durée de quelques millisecondes.

### Fingerprinting

Les _watchers_ exposent un cache simple (de strings), pensé spécifiquement pour ce besoin&nbsp;:&nbsp;si la même erreur reste visible et est détectée
toutes les 0,8 secondes, inutile de la voir apparaître plusieurs fois dans les captures d'écran, les rapports et les logs. Le fingerprint permet
d'ignorer ce qu'on a déjà vu.

### Report

La _callback_ finit par&nbsp;:&nbsp;`watcher.report`.  
Cet appel s'occupe de&nbsp;:

1. Logguer la friction détectée par le watcher,
2. Prendre une capture d'écran comme trace de ce qui a été détecté.

### HumanizedDriver

Rien ne nous empêche de greffer des comportements sur le _logger_ ou sur le _driver_. Ici, le formulaire étant capricieux, on opte pour un test lent
et "humanisé"&nbsp;:&nbsp;saisie avec fautes de frappe, corrections, hésitations. On wrappe simplement le _driver_ dans un _proxy_, `HumanizedDriver`.

## Heisenbugs de concurrence

Ma quête n'était alors pas terminée.  
J'ai vu des collègues compter de 1 à 3 avant de tous cliquer en même temps pour émettre une même action dans l'_open space_. Je me suis alors
questionné sur le sens de ma vie. En procédant de telle sorte, ils ont pourtant vraiment réussi à provoquer des anomalies.

Ce comportement peut être reproduit par Ocarina.  
Par défaut, Ocarina est agressif.

Son option `saturate_workers` permet de forcer du clonage aléatoire de tests à l'intérieur d'une suite.

Dès lors qu'il y a plus de _workers_ disponibles dans la _DriversPool_ que de tests à exécuter dans une suite, Ocarina va alors cloner les tests
aléatoirement, démarrer tous les drivers, et tous leur assigner un test à effectuer.

Il est possible d'activer cette option depuis la fonction `bootstrap`.  
Il est aussi possible de l'activer ou de la désactiver individuellement, soit au niveau d'une suite, soit au niveau d'une campagne. En cas de
contradiction, c'est l'élément le plus profond de l'arborescence qui a le dernier mot. Par exemple, si une campagne dit de désactiver l'option, mais
qu'une suite dit de l'activer, alors la suite prend la priorité.

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

Il est possible de temporairement créer une suite avec seulement un test pour maximiser le ciblage.  
Ou encore de lancer sur plusieurs machines à la fois le cycle (scaling horizontal).

Au-delà des problématiques de concurrence, ce mécanisme de clonage vise également à s'assurer que les tests en succès ne doivent rien au hasard. Cet
effet est amplifié par le degré de scaling horizontal et le nombre de workers impliqués.

<llm-exclude>

---

![Tu es un Mojo lecteur !](/assets/content/docs/creatives/reading-mojo.png)

<p align="center" class="good-work-mojo-msg"><i>Bon travail&nbsp;!<br/>À une prochaine fois, lecteur Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"Retry flaky blocks."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;Yegor Bugayenko, <i><a href="https://github.com/yegor256/prompt" target="_blank" rel="noreferrer">Prompt</a></i></p>

</llm-exclude>
