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

Un setup de travail : un cycle de test complet construit avec Claude Code et Ocarina, contre la démo publique Katalon CURA. Descriptif — ce qui est
là, ce que ça fait.

[📖 Munissez-vous de l'exemple avec IA comme référence.](https://github.com/mojo-molotov/ocarina-with-ai-example)

## Les trois pierres ancestrales

1. `CLAUDE.md` à la racine du projet.
2. `skills/` avec un `<nom>/SKILL.md` par procédure.
3. Règle de vérification : toute affirmation sur le SUT vient d'une observation (sonde, `gh api`, `curl -v`), jamais d'une inférence.

## `CLAUDE.md` (et `CLAUDE.slim.md`)

Deux variantes. `CLAUDE.md` est complet (règles + organisation du projet, hiérarchie, conventions, forme CI, gabarit de PR). `CLAUDE.slim.md` ne
contient que les règles. Slim quand le contexte est chargé ; complet pour l'onboarding et les revues. En cas de divergence, le complet l'emporte.

Les étapes d'onboarding (venv, `pip install`, `ruff` / `mypy` / `pre-commit`, smoke-check du runner) vivent dans `setup-environment`.

Les règles :

**Les tests de sécurité sont fonctionnels et statiques, jamais actifs.** Pas de payloads, pas de requêtes fabriquées, pas de manipulation du DOM via
DevTools. Les scénarios black-hat passent par une UI normale.

**Utiliser des constantes.** Les valeurs nommées ne sont pas inlinées.

**Les datasets sont des décisions humaines.** Proposer n'exécute pas.

**Vérifier empiriquement le comportement du SUT.** Sonde, `gh api`, ou `curl -v`. Jamais d'inférence. Re-dériver à chaque fois : une sonde ne répond
que pour ce qu'elle a exécuté ; un diagnostic antérieur ne répond que pour cette exécution-là.

Chaque règle porte un _pourquoi_ d'une ligne pour que le jugement se déclenche à la frontière.

## `skills/`

Un fichier Markdown par skill, frontmatter YAML + corps. Neuf familles.

### Review (12)

Lectures statiques ; remontent des constats.

- `review-spec-gaps` — questions de clarification sur les SFD.
- `review-watcher-misuse` — `watcher.report(...)` au regard du « négatif uniquement ».
- `review-compartmentalisation-leaks` — URLs, sélecteurs, nombres magiques mal placés.
- `review-report` — classifie chaque FAIL / SKIP d'une exécution.
- Et aussi : `review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers`, `review-comment-drift`,
  `review-suite-stability`, `review-intent-collisions`, `review-watcher-emissions`.

### Analyse (4)

- `analyse-flakiness` — élargit le filet des erreurs transitoires ; les morts chroniques sont de vraies flakes.
- `analyse-fixture-flakiness` — instrumente setup/teardown ; rend visibles les contaminations entre tests.
- `analyse-watcher-flakiness` — avec/sans chaque watcher, balayage d'intervalles.
- `analyse-screenshot-flakiness` — regroupe par `(test, étape, navigateur)`, détecte les différences.

### Black-hat (6)

- `business-attack-ideation` — faire tomber le produit.
- `incoherence-attack-ideation` — chaque étape légale, l'ensemble impossible.
- `persistence-attack-ideation` — tentatives répétées sur une action bloquée.
- `permission-appropriateness-audit` — le modèle d'accès est-il lui-même approprié ?
- `bfcache-exposure-ideation` — attaques BFCache.
- `lateral-resource-ideation` — IDOR via la barre d'adresse uniquement.

### Comprehend (4)

- `assess-test-base` — catalogue la base de test.
- `assess-ecosystem` — recherche publique bornée, plafonnée par budget de tokens.
- `understand-sut-constraints` — bornes SUT qui cassent les tests parallèles.
- `understand-ocarina` — parcourt la doc.

### Pick (3)

Par mtime, jamais par nom de fichier.

- `pick-screenshots`, `pick-logs`, `pick-reports`.

### Author (7)

Chacun produit un livrable.

- `empiricism` — vérifier avant d'encoder ; ne pas écraser un test gap en échec intentionnel.
- `write-a-probe` — script jetable, gitignored.
- `extend-coverage` — étend la couverture à partir des assets existants.
- `update-frd-and-tests` — propage une mise à jour de spec.
- `manual-reproduction-guide` — repro exécutable par un humain.
- `manage-backlog` — `BACKLOG.md`.
- `pr-report` — rapport de PR adapté au type.

### Refactor (2)

- `refactor-fragmentation` — DRY selon préférence utilisateur.
- `introduce-pom-retries` — retries internes aux POMs, avec dédoublement (first-try + with-retries).

### State (1)

- `question-state` — interroger l'environnement avant de croire un résultat.

### Setup (1)

- `setup-environment` — venv, outillage de dev, chemins de drivers dans `CLAUDE.local.md`, boucle pré-commit, smoke-check du runner.

## Chaînes récurrentes

**Suite pas au vert :** `review-report` → `analyse-*` → `write-a-probe` → la trouvaille atterrit dans `IDENTIFIED_GAPS.md` / les SFD / un commentaire
de scénario → sonde supprimée.

**Scénario black-hat prometteur :** `empiricism` → `extend-coverage` (souvent en échec intentionnel).

**Changement de spec :** `update-frd-and-tests` (SFD d'abord, tests ensuite). Les tests gap sont reformulés, pas basculés.

**Nouvelle primitive Ocarina :** `understand-ocarina` d'abord, écriture ensuite.

## Discipline

**Remonter, ne pas appliquer.** Les skills produisent ; l'utilisateur décide.

**Empirique plutôt qu'assertif.** Toute affirmation SUT est observée, citée, datée. Phrase rituelle : _« Juste remarque, je suppose. Je vérifie
empiriquement. »_

**Les tests gap sont reformulés, pas basculés au vert.** Inverser l'assertion, renommer, déplacer la ligne dans le doc de stratégie, consigner la date
dans `IDENTIFIED_GAPS.md`. Le tout via `update-frd-and-tests`.

**Les signaux watchers sont négatifs uniquement.** Un watcher qui émet _« login réussi »_ casse le contrat.

**Priorité au scaling horizontal.** Pas d'état en mémoire au niveau du worker. Primitives distribuées uniquement.

**Mtime, pas nom de fichier.** Les suffixes UUID sont aléatoires ; `pick-*` trie par mtime.

## Ce que ce setup n'est pas

- Ne génère pas de tests de façon autonome.
- Ne patche pas les hallucinations en CI ; un échec déclenche `review-report` + `analyse-*`.
- Ne réécrit pas la spec ; seul `update-frd-and-tests` le fait, avec une ligne de révision.
- Ne fait pas de tests de sécurité actifs. Jamais.

## Ressources exposées

- https://mojo-molotov.github.io/ocarina-holy-book/llms.txt
- https://mojo-molotov.github.io/ocarina-holy-book/llms-full.txt
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.md
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.slim.md
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-en.pdf
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-fr.pdf

<llm-exclude>

---

![Mojo qui joue de l'ocarina](/assets/content/docs/creatives/mojo-playing-ocarina.png)

<p align="center" class="good-work-mojo-msg"><i>Oh wow !<br/>Tu l'as déjà bien bidouillé à ta sauce, lecteur Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"On Earth and Space, he has all the tricks."</p>

<p align="right" class="inspiring-quote-author">― ▒▒█𝚃𝙾𝙿 𝚂𝙴𝙲𝚁█𝚃 // 𝚂𝙲𝙸 // 𝙽▒▒▒▒𝙾𝙵𝙾𝚁𝙽</p>

</llm-exclude>
