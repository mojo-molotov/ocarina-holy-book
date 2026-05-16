---
sticky: 1
description: Hello it's me, your new best friend!

date: 2026-05-16

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-playing-ocarina.png
---

# Utiliser Ocarina avec l'IA

Cette page décrit un setup de travail concret : un cycle de test complet construit et maintenu avec Claude Code et Ocarina. Le système sous test est
la démo publique Katalon CURA. L'objectif ici est purement descriptif : quels fichiers existent, à quoi ils servent, comment ils se combinent.

[📖 Munissez-vous de l'exemple avec IA comme référence.](https://github.com/mojo-molotov/ocarina-with-ai-example)

## Les trois pierres ancestrales

1. Un fichier `CLAUDE.md` à la racine du projet.
2. Un dossier `skills/` contenant un `<nom>/SKILL.md` par procédure.
3. Une règle de vérification : toute affirmation sur le comportement du SUT doit venir d'une observation (une sonde, un `gh api`, un `curl -v`),
   jamais d'une inférence.

## `CLAUDE.md`

Le fichier encode les règles qui ne changent pas entre les tours. Quelques exemples portants côté CURA.

**Les tests de sécurité sont fonctionnels et statiques, jamais actifs.** Toute la famille black-hat (saturation, persistance, accès latéral,
expositions BFCache) est tenue par cette règle. Pas de payload d'injection. Pas de fabrication de requête. Pas de manipulation du DOM via les
DevTools. Chaque scénario d'attaque doit être atteignable par une motion UI normale.

**Utiliser des constantes.** Si une valeur a un nom (`DEMO_USERNAME`, `LOGIN_URL`), on n'inline pas.

**La constitution des jeux de données implique des décisions à prendre par un humain.** Quand l'assistant propose d'ajouter ou de modifier un dataset,
l'exécution ne suit pas automatiquement.

**Vérifier empiriquement le comportement du SUT.** Une affirmation sur ce que fait CURA vient d'une sonde qui a capturé le HTML, d'un `gh api` qui a
lu le PHP déployé, ou d'un `curl -v` qui a lu les en-têtes. Jamais d'une inférence.

Chaque règle porte un _pourquoi_ d'une ligne (souvent un incident passé), pour que l'assistant puisse exercer son jugement aux limites plutôt que de
pattern-matcher la règle.

## `skills/`

Chaque skill est un fichier Markdown unique, avec un frontmatter YAML (`name`, `description`) et un corps qui déroule une procédure de bout en bout.
Ils se regroupent en huit familles.

### Review (12)

Lectures statiques de la codebase ou des specs. Les skills remontent des constats, l'utilisateur applique.

- `review-spec-gaps` lit les SFD à la manière d'un analyste QA et remonte des questions de clarification.
- `review-watcher-misuse` vérifie chaque appel à `watcher.report(...)` au regard de la convention « négatif uniquement ».
- `review-compartmentalisation-leaks` détecte les URLs hors de `src/constants/urls.py`, les sélecteurs hors des POMs, les nombres magiques inline.
- `review-report` classifie chaque FAIL (corps, setup, teardown) et chaque SKIP (statique, smoke-gate, setup-error, cycle-policy) pour une exécution
  donnée.
- Et aussi : `review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers`, `review-comment-drift`,
  `review-suite-stability`, `review-intent-collisions`, `review-watcher-emissions`.

### Analyse (4)

- `analyse-flakiness` élargit le filet de capture des erreurs transitoires pour que toutes les exceptions soient retentées ; les morts chroniques
  après N rejeux sont très probablement des tests flaky.
- `analyse-fixture-flakiness` instrumente la frontière setup/teardown pour rendre visibles les contaminations entre tests.
- `analyse-watcher-flakiness` exécute la suite avec et sans chaque watcher, sur un balayage d'intervalles de poll.
- `analyse-screenshot-flakiness` regroupe les captures par `(test, étape, navigateur)` et y analyse la présence de comportements différents ou non.

### Black-hat (6)

- `business-attack-ideation` essaie de faire "tomber" le produit.
- `incoherence-attack-ideation` couvre les combinaisons d'actions individuellement autorisées mais incohérentes en tant qu'ensemble (par exemple : une
  même personne réserve des hôtels pour elle dans deux villes avec une fenêtre de temps qui rend le trajet physiquement impossible).
- `persistence-attack-ideation` couvre les tentatives répétées d'effectuer une action bloquée sur le SUT.
- `permission-appropriateness-audit` lit le modèle d'accès et pose la question _« cette parité est-elle voulue ? »_.
- `bfcache-exposure-ideation` identifie des attaques BFCache.
- `lateral-resource-ideation` reprend l'esprit d'IDOR, mais restreint à la manipulation depuis la barre d'adresse (pas d'interception de requête, pas
  de proxy).

### Comprehend (4)

- `assess-test-base` catalogue la base de test.
- `assess-ecosystem` fait une passe de recherche bornée sur des sources publiques, encadrée par un budget de tokens (un tiers du budget restant par
  défaut).
- `understand-sut-constraints` cartographie les bornes côté SUT qui font dérailler _le code de test_ sous parallélisme (par exemple : nombre max de
  sessions. simultanées pour un utilisateur).
- `understand-ocarina` parcourt la documentation.

### Pick (3)

Récupérer les bons fichiers en sortie d'exécution.

- `pick-screenshots`, `pick-logs`, `pick-reports`.

### Author (7)

Skills de workflow qui produisent un livrable.

- `empiricism` : vérifier avant d'encoder ; ne jamais écraser un test gap en échec intentionnel.
- `write-a-probe` : script Python jetable dans un dossier gitignored.
- `extend-coverage` : étend la couverture des tests sur la base d'un patrimoine.
- `update-frd-and-tests` : propagation d'une mise à jour des spécifications.
- `manual-reproduction-guide` : produit un scénario de reproduction manuel.
- `manage-backlog` : gère un backlog (`BACKLOG.md`).
- `pr-report` : produit un rapport de PR adapté au type (refactoring, stratégie de test, correction de bug, doc).

### Refactor (2)

- `refactor-fragmentation` applique le principe DRY selon les préférences de l'utilisateur.
- `introduce-pom-retries` produit des retries internes aux POMs pour lutter contre la flakiness, avec dédoublement du test : une variante _first-try_
  (sans retry, échec intentionnel jusqu'à correction de l'anomalie) et une variante _with-retries_ (qui passe grâce aux retries POM, afin de maintenir
  la couverture stable).

### State (1)

- `question-state` : analyse les états du SUT (par exemple : dyno chaud ou froid, artefacts résiduels, propreté du profil navigateur, concurrence des
  workers, mises à jour récentes, contention liée à l'heure...).

## Chaînes récurrentes

Les skills se combinent. Quelques enchaînements qui reviennent souvent :

**Lorsque tout n'est pas au vert :**

1. `review-report` classifie chaque incident (FAIL : corps, setup ou teardown ; SKIP : statique, smoke-gate, setup-error ou cycle-policy).
2. Selon la classe d'incident, on enchaîne avec `analyse-flakiness`, `analyse-fixture-flakiness` ou `analyse-screenshot-flakiness`.
3. `write-a-probe` isole la cause racine.
4. La trouvaille est consignée dans `IDENTIFIED_GAPS.md`, dans les SFD, ou dans un commentaire de scénario.
5. La sonde est supprimée.

**Lorsqu'un scénario black-hat semble prometteur :**

1. `empiricism` vérifie le comportement actuel de CURA.
2. `extend-coverage` écrit le test, souvent comme échec intentionnel, tant que le SUT n'a pas corrigé le comportement.

**Lorsqu'une spec change :**

1. `update-frd-and-tests` met à jour le document de suivi des SFD en premier, avec une raison en une phrase.
2. Les tests sont ensuite adaptés.
3. Si un test gap est concerné par la correction, il est reformulé (l'assertion est inversée, le test est renommé, sa catégorie dans le doc de
   stratégie passe d'intentional-fail à pass-everywhere) plutôt que simplement modifié pour passer au vert.

**Lorsqu'une nouvelle primitive Ocarina est nécessaire :**

1. `understand-ocarina` consulte d'abord le Holy Book.
2. L'écriture vient ensuite.

## Discipline

Plusieurs patterns se retrouvent dans toutes les procédures.

**Remonter, ne pas appliquer.** Chaque skill se termine de la même façon : imprimer le catalogue, s'arrêter, laisser l'utilisateur trancher.

**Empirique plutôt qu'assertif.** Toute affirmation sur le comportement du SUT est adossée à une observation, citée sur place, datée. La phrase
rituelle : _« Juste remarque, je suppose. Je vérifie empiriquement. »_ Elle déclenche un `write-a-probe`, la sonde capture la vérité, la trouvaille
atterrit, la sonde est supprimée.

**Les tests gap sont reformulés, pas basculés au vert.** Quand CURA corrige un gap §9, le test en échec intentionnel ne peut pas être simplement édité
pour correspondre au nouveau comportement. La discipline : inverser l'assertion, renommer le test, déplacer sa ligne dans le doc de stratégie de la
catégorie intentional-fail vers pass-everywhere, mettre à jour `IDENTIFIED_GAPS.md` avec la date de résolution. Le tout en une seule motion via
`update-frd-and-tests`.

**Les émissions des watchers sont systématiquement des signaux négatifs.** Un watcher qui émet _« login réussi »_ casse le contrat.
`review-watcher-misuse` audite les callbacks ; `review-watcher-emissions` lit les sorties d'exécution en sachant que toute émission est, par
convention, indésirable.

**Priorité au scaling horizontal.** Quand une couche de coordination est proposée, la question est _« est-ce que ça fonctionne avec un process, trois
process, N process ? »_. L'état en mémoire au niveau du worker Ocarina est rejeté par construction. Primitives distribuées uniquement : compteurs
adossés à Redis, verrous distribués, systèmes de réservation.

**Identification des artefacts générés d'après leur date.** Captures d'écran, logs, rapports : tous portent un suffixe UUID aléatoire. Les trois
skills `pick-*` existent pour empêcher tout tri lexicographique.

## Ce que ce setup n'est pas

- Générer des tests de façon autonome.
- Patcher des hallucinations en CI. Un test qui échoue déclenche `review-report` et un skill `analyse-*`.
- Réécrire la spec. Le document de suivi des SFD n'est édité que via `update-frd-and-tests`, avec une ligne d'historique de révision.
- Faire des tests de sécurité actifs. Ni maintenant, ni jamais.

<llm-exclude>

---

![Mojo qui joue de l'ocarina](/assets/content/docs/creatives/mojo-playing-ocarina.png)

<p align="center" class="good-work-mojo-msg"><i>Oh wow !<br/>Tu l'as déjà bien bidouillé à ta sauce, lecteur Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"On Earth and Space, he has all the tricks."</p>

<p align="right" class="inspiring-quote-author">― ▒▒█𝚃𝙾𝙿 𝚂𝙴𝙲𝚁█𝚃 // 𝚂𝙲𝙸 // 𝙽▒▒▒▒𝙾𝙵𝙾𝚁𝙽</p>

</llm-exclude>
