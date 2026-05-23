---
sticky: 1
pagefind-indexed: false

description: Les frameworks de test ont tous fait le même mauvais pari. Ocarina fait le contraire. Apprenez pourquoi.

date: 2026-04-24

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/what-is-it/creatives/the-children-tools-battle.png
---

# Qu'est donc Ocarina ?

Ocarina a été conçu pour permettre de créer **le plus facilement possible** des tests automatisés via navigateur web, en laissant un **contrôle total
à son utilisateur**.

## Encore un !

### Eux

La plupart des frameworks de test ont été conçus dans un monde où la barrière entre "ceux qui codent" et "ceux qui définissent les tests" était réelle
et structurelle.

_Robot Framework_, a essayé de la **contourner** avec un _DSL_ (_Domain Specific Language_), incluant **leur propre format** et **leur propre
écosystème de plugins**. Ainsi, RF impose de-facto ses propres standards&nbsp;:&nbsp;c'est le coût immédiat de sa promesse.

De la même sorte, _Cucumber_ a essayé avec le _Gherkin_&nbsp;:&nbsp;un langage "naturel" qui, en pratique, **contraint tout le monde sans vraiment
libérer personne**. Coût&nbsp;:&nbsp;**couche de traduction permanente, désynchronisation Gherkin/code**.

Tous ont parié sur la même chose : **masquer la complexité** pour réconcilier les profils.  
Résultat : les non-techniques restent spectateurs, et les techniques se retrouvent **prisonniers d'un outil qu'ils n'auraient jamais choisi**.

Le coût le plus important est un **nivellement par le bas, la réduction des options et une "flexibilité" qui s'obtient en se _battant_ contre des
_outils_ plutôt que d'utiliser des _solutions_**.

![Illustration d'enfants qui jouent avec une pelotte de nœuds en tirant chacun sur une corde, chacun brandissant un drapeau de sa "SOLUTION"](/assets/content/what-is-it/creatives/the-children-tools-battle.png)

<p align="center"><i>Rien ne sert que chacun tire sur la corde qu'on lui tend si, au centre, il n'y a qu'un nœud gordien.</i></p>

### Nous

![Illustration d'un personnage décontracté qui joue simplement de l'ocarina dans son propre cadre, peu importe le chaos ambiant, l'ocarina dans une main et une fleur dans l'autre](/assets/content/what-is-it/creatives/skull-kid-playing-out-there.png)

<p align="center"><i>Mieux vaut être seul que mal accompagné.</i></p>

**Ocarina parie sur le contraire :** cette barrière va disparaître. Il s'agit d'un non-débat sur lequel tout le monde s'est construit un nœud autour
du cou. Outils honteusement compliqués, vendus comme "solutions". Impact&nbsp;:&nbsp;**désastre opérationnel** dès lors que l'on a un besoin qui ne
peut pas s'exprimer dans un "cadre" qui n'est PAS réellement générique.

Et le pire&nbsp;:&nbsp;**toutes ces technologies continueront d'évoluer dans ce sens**. AUCUNE d'entre elle ne prendra ce _shift_, puisqu'il s'agit
d'un changement de paradigme et d'**un retour aux fondamentaux qui contredit totalement leur proposition de valeur**.

Pourtant, ce qu'il nous reste à présent, c'est le besoin d'un code de test **lisible, traçable et flexible**, sous sa forme la plus **brute**.

Avec l'IA, et des outils comme _Claude Code_, ce pari devient chaque jour plus solide.  
Le pont entre techniques et non-techniques n'est plus une couche d'abstraction.

**C'est l'IA elle-même. IA qui travaille sur de la donnée brute.**

## Le problème culturel

Il y a un autre angle mort, rarement nommé&nbsp;:&nbsp;**la méthodologie**.

### ISTQB, où es-tu ?

L'ISTQB et les testeurs professionnels ont construit, depuis des décennies, un vocabulaire précis et éprouvé&nbsp;:&nbsp;_cycles de test_,
_campagnes_, _suites de test_, _cas de test_, _pas de test_. Une hiérarchie claire, pensée pour **organiser, tracer et piloter** la qualité
logicielle.

Les outils automatisés, eux, ont **largement ignoré cet héritage**.

_pytest_, _Jest_, _Mocha_... tous sont **un mix hybride** où les testeurs doivent apprendre à penser comme des développeurs, et où personne ne parle
vraiment la même langue.

![Illustration de deux camps n'arrivant pas à se comprendre tout en croyant parler la même langue](/assets/content/what-is-it/creatives/speaking-nonsense.png)

<p align="center"><i>Cette "méthode des deux langues" est un échec.</i></p>

### Retour aux fondamentaux

**Ocarina ne fait pas ce compromis.**

Sa structure est modélisée **directement et exclusivement** sur la méthodologie des testeurs. Chaque concept du code correspond à un concept métier du
test. Pas d'emprunt, pas de détournement, pas de _"ça ressemble à peu près à"_.

Et parce qu'Ocarina prend ce pari jusqu'au bout&nbsp;:&nbsp;**il est entièrement autonome**. Pas de plugin pytest. Pas d'intégration forcée à un
écosystème tiers. Ocarina est _batteries-included_, il n'a besoin de rien d'autre pour fonctionner et c'est un choix délibéré.

## Le vrai point de douleur

### De la "créativité"

Tout le monde s'acharne sur le _comment_&nbsp;:&nbsp;des interfaces, des abstractions, de "jolis" DSLs.  
Pendant ce temps, le _pourquoi_ disparaît.

**Ocarina fait le choix inverse.**

Toute sa conception ainsi que tout son livre sacré, sont focalisés sur le **pourquoi**, sur de réels problèmes.  
Pas sur une abstraction à utiliser _"comme on aime"_.

Pour le _comment_ ?  
La réponse est simple&nbsp;:&nbsp;Ocarina est **dense, immédiatement opérationnel et strict**. Pensé pour que les humains ainsi que les LLMs en
comprennent le cœur et l'usage sans friction.

### Que dit la science ?

Ici, tout repose sur des **fondations statiques**&nbsp;:

- typage,
- generics,
- programmation fonctionnelle.

Ocarina rend son mésusage difficile par conception&nbsp;:&nbsp;le compilateur fait foi.

![Illustration d'un personnage en état de plénitude grâce à une transe algébrique](/assets/content/what-is-it/creatives/algebraic-fullness.png)

<p align="center"><i><strong>Juste de l'algèbre.</strong></i></p>

> 📖 Le mot "algèbre" vient de l'arabe الجبر (al-jabr), qui signifie "la réunion des parties brisées" ou "la réduction des fractures".

La plupart des outils partent de la grammaire humaine pour soi-disant "formaliser".  
Puis, on réalise qu'une machine ne peut pas la lire telle quelle.  
Alors, on empile les "adaptateurs".

**Nous n'appelons pas ça de la _formalisation_ mais des _vues de l'esprit_.**

Ocarina fait évidemment **l'inverse**.  
C'est ce qui rend Ocarina **stable et extensible à la fois**.

## Vision

### Grammaire souveraine

_Et si déléguer sa grammaire à des "standards" n'avait jamais été une bonne idée&nbsp;?_

Le vrai hiatus du test E2E **n'est pas d'imposer la "meilleure" novlangue**.  
Réponse simple&nbsp;:&nbsp;Ocarina est **extensible**.

On y crée les verbes et conjonctions que l'on veut, le tout régi par des **règles strictes qui poussent l'ensemble à rester profondément cohérent**.

Il reste alors à garantir la **traçabilité et la robustesse**.

### Né sur le terrain

Dans Ocarina, chaque étape est observable.  
Le chemin d'erreur est explicite. Le rapport de test **émerge naturellement du code**.

Pas de surarchitecture. Pas de dépendances inutiles.  
Juste quelque chose de **petit, lisible, et qui tient dans le temps**.

Le plus fort, c'est qu'**Ocarina n'invente rien&nbsp;:&nbsp;Ocarina en revient aux fondamentaux**.

### Adoption

Pour les scénarios les plus extrêmes&nbsp;:&nbsp;Ocarina n'a pas besoin d'être installé.  
Il se copie, s'adapte, et tourne.  
Pas de dépendance à auditer.

Pour les équipes bloquées par des _politiques de sécurité_&nbsp;:&nbsp;le code est petit, auditable en une après-midi. Rien de caché. Les seules
dépendances externes sont dans les plugins post-exécution et si l'une d'elles ne passe pas, elle se retire sans que le reste ne casse.

En pratique, un consultant peut arriver chez un client avec Ocarina dans sa poche, _presque_ sans demander la permission à personne.

![Illustration d'un personnage qui est enfin libre après une longue période de contraintes aberrantes](/assets/content/what-is-it/creatives/free-mojo-fr.png)

<p align="center"><i>Ce ne sont pas les hommes qui fatiguent, mais les vieilles ficelles qui les usent.</i></p>

Et c'est aussi pour ces raisons qu'il existe : pour rendre aux testeurs leur **indépendance**.  
Le tout avec un **bijou de synthèse**.

<p align="right"><i>Игорь Казанова</i></p>
