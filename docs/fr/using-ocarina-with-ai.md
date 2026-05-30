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

Un setup de travail&nbsp;:&nbsp;un cycle de test complet construit avec Claude Code et Ocarina, contre la démo publique Katalon CURA.

[📖 Munissez-vous de l'exemple avec IA comme référence.](https://github.com/mojo-molotov/ocarina-with-ai-example)

## Les trois pierres ancestrales

1. `CLAUDE.md` à la racine du projet.
2. `skills/` avec un `<nom>/SKILL.md` par procédure.
3. Règle de vérification&nbsp;:&nbsp;toute affirmation sur le SUT vient d'une observation (sonde, `gh api`, `curl -v`), jamais d'une inférence.

## `CLAUDE.md`

Deux variantes. `CLAUDE.md` est complet (règles&nbsp;+&nbsp;organisation du projet, hiérarchie, conventions, forme CI, gabarit de PR).
`CLAUDE.slim.md` ne contient que les règles. Slim quand le contexte est chargé&nbsp;;&nbsp;complet pour l'onboarding et les revues. En cas de
divergence, le complet l'emporte.

Les étapes d'onboarding (venv, `pip install`, la batterie de skills copiée dans Claude Code, `ruff`&nbsp;/&nbsp;`mypy`&nbsp;/&nbsp;`pre-commit`,
smoke-check du runner) vivent dans `setup-environment`.

Les règles&nbsp;:

**Les tests de sécurité sont fonctionnels et statiques, jamais actifs.** Pas de payloads, pas de requêtes forgées, pas de manipulation du DOM via
DevTools. Les scénarios black-hat passent par une UI normale.

**Utiliser des constantes.** Les valeurs nommées ne sont pas inlinées.

**Les datasets sont des décisions humaines.** Proposer, PAS exécuter.

**Vérifier empiriquement le comportement du SUT.** Sonde, `gh api`, ou `curl -v`. Jamais d'inférence. Re-dériver à chaque fois&nbsp;:&nbsp;une sonde
ne répond que pour ce qu'elle a exécuté&nbsp;;&nbsp;un diagnostic antérieur ne répond que pour cette exécution-là.

Chaque règle contient un "_pourquoi_" d'une ligne.

## `skills/`

Un fichier Markdown par skill, frontmatter YAML + corps. Dix familles.

### Review (14)

Lectures statiques&nbsp;;&nbsp;remontent des constats.

- `review-spec-gaps`&nbsp;—&nbsp;questions de clarification sur les SFD.
- `review-watcher-misuse`&nbsp;—&nbsp;`watcher.report(...)` principe de « négatif uniquement ».
- `review-compartmentalisation-leaks`&nbsp;—&nbsp;URLs, sélecteurs, nombres magiques aux mauvais endroits.
- `review-dead-code`&nbsp;—&nbsp;connecteurs&nbsp;/&nbsp;POMs&nbsp;/&nbsp;scénarios&nbsp;/&nbsp;suites&nbsp;/&nbsp;fragments&nbsp;/&nbsp;constantes
  non utilisés&nbsp;;&nbsp;au cas par cas&nbsp;:&nbsp;supprimer, mettre en incubateur (`<racine-source>/incubator/`, arbre de dépendances préservé),
  ou conserver.
- `review-hierarchy-naming`&nbsp;—&nbsp;parent ⊃ enfant de même nom dans l'arbre du cycle (le plus souvent
  `Campaign("X") ⊃ Suite("X")`)&nbsp;;&nbsp;renommer l'enfant pour son vrai périmètre de segment (la hiérarchie est stricte&nbsp;—&nbsp;pas
  d'aplatissement possible).
- `review-report`&nbsp;—&nbsp;classifie chaque FAIL&nbsp;/&nbsp;SKIP d'une exécution.
- Et&nbsp;:&nbsp;`review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers`,
  `review-comment-drift`, `review-suite-stability`, `review-intent-collisions`, `review-watcher-emissions`.

### Analyse (4)

- `analyse-flakiness`&nbsp;—&nbsp;élargit le filet des erreurs transitoires&nbsp;;&nbsp;les morts chroniques sont de vraies flakes.
- `analyse-fixture-flakiness`&nbsp;—&nbsp;instrumente setup/teardown&nbsp;;&nbsp;rend visibles les contaminations entre tests.
- `analyse-watcher-flakiness`&nbsp;—&nbsp;analyse la fiabilité des watchers.
- `analyse-screenshot-flakiness`&nbsp;—&nbsp;regroupe par `(test, étape, navigateur)`, détecte les différences.

### Black-hat (6)

- `business-logic-vulnerability-ideation`&nbsp;—&nbsp;faire tomber le produit.
- `incoherence-attack-ideation`&nbsp;—&nbsp;chaque étape légale prise isolément, incohérent quand combinées pour construire un ensemble invalide.
- `persistence-attack-ideation`&nbsp;—&nbsp;tentatives répétées sur une action bloquée.
- `permission-appropriateness-audit`&nbsp;—&nbsp;le modèle d'accès est-il lui-même approprié&nbsp;?
- `bfcache-exposure-ideation`&nbsp;—&nbsp;attaques BFCache.
- `lateral-resource-ideation`&nbsp;—&nbsp;IDOR via la barre d'adresse uniquement.

### Comprehend (4)

- `assess-test-base`&nbsp;—&nbsp;catalogue la base de test.
- `assess-ecosystem`&nbsp;—&nbsp;recherche publique bornée, plafonnée par budget de tokens.
- `understand-sut-constraints`&nbsp;—&nbsp;bornes SUT qui cassent les tests parallèles.
- `understand-ocarina`&nbsp;—&nbsp;parcourt la doc.

### Pick (3)

Par mtime, jamais par nom de fichier.

- `pick-screenshots`, `pick-logs`, `pick-reports`.

### Author (9)

Chacun produit un livrable.

- `empiricism`&nbsp;—&nbsp;vérifier avant d'encoder&nbsp;;&nbsp;ne pas écraser un test gap en échec intentionnel.
- `write-a-probe`&nbsp;—&nbsp;script jetable, gitignored.
- `write-test-strategy`&nbsp;—&nbsp;génère le document de stratégie de test à partir de la suite (scope, types, tables de couverture, arbre du cycle,
  pass/fail, gaps, matrice CI).
- `plan-test-effort`&nbsp;—&nbsp;plan d'effort de test « premier jet », naïf&nbsp;;&nbsp;criticité (critique/majeure/mineure), registre de risques
  léger, poids S&nbsp;/&nbsp;M&nbsp;/&nbsp;L, questions ouvertes pour la passe approfondie.
- `extend-coverage`&nbsp;—&nbsp;étend la couverture à partir du patrimoine existant.
- `update-frd-and-tests`&nbsp;—&nbsp;propage une mise à jour de spec dans la SFD interne au projet&nbsp;;&nbsp;les systèmes amont (Confluence, Jira,
  …) restent en lecture seule.
- `manual-reproduction-guide`&nbsp;—&nbsp;repro exécutable par un humain.
- `manage-backlog`&nbsp;—&nbsp;`BACKLOG.md`.
- `pr-report`&nbsp;—&nbsp;rapport de PR adapté au type.

### Refactor (2)

- `refactor-fragmentation`&nbsp;—&nbsp;DRY selon préférence utilisateur.
- `introduce-pom-retries`&nbsp;—&nbsp;retries internes aux POMs, avec dédoublement (first-try + with-retries).

### State (1)

- `question-state`&nbsp;—&nbsp;interroger l'environnement avant de croire un résultat.

### Setup (1)

- `setup-environment`&nbsp;—&nbsp;venv, outillage de dev, la batterie de skills Ocarina copiée dans le répertoire de skills de Claude Code, chemins de
  drivers dans `CLAUDE.local.md`, boucle pré-commit, smoke-check du runner.

### Run (1)

- `propose-visual-review`&nbsp;—&nbsp;avant un lancement local, propose `--not-headless` (regarder le navigateur exécuter) vs headless (comme en CI).
  Compose la commande&nbsp;;&nbsp;l'utilisateur la lance.

## Chaînes récurrentes

**Cycle en échec&nbsp;:**&nbsp;`review-report`&nbsp;→&nbsp;`analyse-*`&nbsp;→&nbsp;`write-a-probe`&nbsp;→&nbsp;trouvailles propagées dans
`IDENTIFIED_GAPS.md` /&nbsp;les SFD&nbsp;/&nbsp;un commentaire de scénario&nbsp;→&nbsp;sonde supprimée.

**Scénario black-hat prometteur&nbsp;:**&nbsp;`empiricism`&nbsp;→&nbsp;`extend-coverage` (souvent en échec intentionnel).

**Changement de spec&nbsp;:**&nbsp;`update-frd-and-tests` (SFD d'abord, tests ensuite). Les tests gap sont reformulés, pas basculés.

**Nouvelle primitive Ocarina&nbsp;:**&nbsp;`understand-ocarina` d'abord, écriture ensuite.

**Lorsque l'on est sur le point de lancer une exécution&nbsp;:**&nbsp;`propose-visual-review`&nbsp;—&nbsp;headed (`--not-headless`) ou headless (comme
en CI)&nbsp;? Compose la commande&nbsp;;&nbsp;l'utilisateur la lance.

## Discipline

**Remonter, ne pas appliquer.** Les skills produisent&nbsp;;&nbsp;l'utilisateur décide.

**Empirique plutôt qu'assertif.** Toute affirmation SUT est observée, citée, datée. Phrase rituelle&nbsp;:&nbsp;_«&nbsp;Juste remarque, je suppose. Je
vérifie empiriquement.&nbsp;»_

**Les tests gap sont reformulés, pas basculés au vert.** Inverser l'assertion, renommer, déplacer la ligne dans le doc de stratégie, consigner la date
dans `IDENTIFIED_GAPS.md`. Le tout via `update-frd-and-tests`.

**Les signaux des watchers sont toujours négatifs.** Un watcher qui émet _«&nbsp;login réussi&nbsp;»_ casse le contrat.

**Distribué quand une ressource est partagée.** Dès que plusieurs workers se partagent une ressource plafonnée par le SUT (sessions, créneaux,
quotas), la coordination passe par des primitives distribuées. Sinon, un cache local en mémoire suffit&nbsp;—&nbsp;à condition que les clés soient
garanties uniques et que leur génération soit thread-safe.

**Mtime, pas nom de fichier.** Les suffixes UUID sont aléatoires&nbsp;;&nbsp;`pick-*` trie par mtime.

## Ce que ce setup n'est pas

- Ne génère pas de tests de façon autonome.
- Ne patche pas les hallucinations en CI&nbsp;;&nbsp;un échec déclenche `review-report`&nbsp;+&nbsp;`analyse-*`.
- Ne réécrit pas la spec&nbsp;;&nbsp;seul `update-frd-and-tests` le fait, avec une ligne de révision.
- Ne fait pas de tests de sécurité actifs. Jamais.

## Ressources exposées

- https://mojo-molotov.github.io/ocarina-holy-book/llms.txt
- https://mojo-molotov.github.io/ocarina-holy-book/llms-full.txt
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.md
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.slim.md
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-ru.pdf
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-en.pdf
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-fr.pdf

<llm-exclude>

---

![Mojo qui joue de l'ocarina](/assets/content/docs/creatives/mojo-playing-ocarina.png)

<p align="center" class="good-work-mojo-msg"><i>Oh wow&nbsp;!<br/>Tu l'as déjà bien bidouillé à ta sauce, lecteur Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"On Earth and Space, he has all the tricks."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;▒▒█𝚃𝙾𝙿 𝚂𝙴𝙲𝚁█𝚃 //&nbsp;𝚂𝙲𝙸 //&nbsp;𝙽▒▒▒▒𝙾𝙵𝙾𝚁𝙽</p>

</llm-exclude>
