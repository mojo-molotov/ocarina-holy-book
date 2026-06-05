---
sticky: 1
description: Hello it's me, your new best friend!

date: 2026-05-16

head:
  - - meta
    - property: og:image
      content: https://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-playing-ocarina.png
---

# Использование Ocarina с AI

Рабочая конфигурация: полный цикл тестирования, собранный связкой Claude Code и Ocarina, против публичного демо Katalon CURA.

[📖 Возьмите за образец AI-пример.](https://github.com/mojo-molotov/ocarina-with-ai-example)

## Три духовных камня

1. `CLAUDE.md` в корне проекта.
2. `skills/` с одним `<name>/SKILL.md` на каждую процедуру.
3. Правило проверки: каждое утверждение о SUT идёт от наблюдения (probe, `gh api`, `curl -v`), а не от домысла.

## `CLAUDE.md`

Два варианта. `CLAUDE.md` — полный (правила + структура проекта, иерархия, соглашения, устройство CI, шаблон PR). `CLAUDE.slim.md` — только правила.
Slim — когда контекст перегружен; полный — для онбординга и ревью. При расхождении побеждает полный.

Шаги онбординга (venv, `pip install`, набор скиллов, скопированный в Claude Code, `ruff`&nbsp;/&nbsp;`mypy`&nbsp;/&nbsp;`pre-commit`, smoke-проверка
раннера) описаны в `setup-environment`.

Правила:

**Тестирование безопасности функциональное и статичное — никогда активное.** Никаких пейлоадов, никаких сфабрикованных запросов, никаких манипуляций с
DOM через DevTools. Сценарии чёрных шляп идут через обычный пользовательский интерфейс.

**Используйте константы.** Именованные значения не вписывают прямо в код.

**Наборы данных — это решения людей.** Предложить — не значит запустить.

**Проверяйте поведение SUT эмпирически.** Probe, `gh api` или `curl -v`. Никогда не домысел. Выводите заново каждый раз: probe отвечает только за то,
что он реально прогнал; прежний диагноз — только для того прогона.

У каждого правила есть однострочное «_почему_».

## `skills/`

Один файл Markdown на каждый навык, YAML-frontmatter + тело. Десять семейств.

### Ревью (14)

Статическое чтение; выносят находки на поверхность.

- `review-spec-gaps`&nbsp;—&nbsp;уточняющие вопросы по FRD.
- `review-watcher-misuse`&nbsp;—&nbsp;`watcher.report(...)` вопреки соглашению «только негатив».
- `review-compartmentalisation-leaks`&nbsp;—&nbsp;URL, селекторы, магические числа не на своём месте.
- `review-dead-code`&nbsp;—&nbsp;неиспользуемые
  connectors&nbsp;/&nbsp;POM&nbsp;/&nbsp;сценарии&nbsp;/&nbsp;suites&nbsp;/&nbsp;фрагменты&nbsp;/&nbsp;константы; для каждой находки: удалить,
  инкубировать (`<source-root>/incubator/`, дерево зависимостей сохранено) или оставить.
- `review-hierarchy-naming`&nbsp;—&nbsp;родитель ⊃ потомок с тем же именем в дереве цикла (чаще всего `Campaign("X") ⊃ Suite("X")`); переименовать
  потомка под его реальный сегмент (иерархия строгая — сплющивание невозможно).
- `review-report`&nbsp;—&nbsp;классифицировать каждый FAIL&nbsp;/&nbsp;SKIP за один прогон.
- Плюс: `review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers`, `review-comment-drift`,
  `review-suite-stability`, `review-intent-collisions`, `review-watcher-emissions`.

### Анализ (4)

- `analyse-flakiness`&nbsp;—&nbsp;расширить сеть transient-error; хронические падения — это настоящие flakes.
- `analyse-fixture-flakiness`&nbsp;—&nbsp;инструментировать setup/teardown; вынести на поверхность перекрёстное загрязнение тестов.
- `analyse-watcher-flakiness`&nbsp;—&nbsp;с каждым watcher и без него, перебор интервалов.
- `analyse-screenshot-flakiness`&nbsp;—&nbsp;сгруппировать по `(test, step, browser)`, выявить различия.

### Чёрная шляпа (6)

- `business-logic-vulnerability-ideation`&nbsp;—&nbsp;обрушить продукт.
- `incoherence-attack-ideation`&nbsp;—&nbsp;каждый шаг легален, набор невозможен.
- `persistence-attack-ideation`&nbsp;—&nbsp;упорные повторы заблокированных действий.
- `permission-appropriateness-audit`&nbsp;—&nbsp;уместна ли сама модель доступа?
- `bfcache-exposure-ideation`&nbsp;—&nbsp;атаки на BFCache.
- `lateral-resource-ideation`&nbsp;—&nbsp;IDOR только через адресную строку.

### Понимание (4)

- `assess-test-base`&nbsp;—&nbsp;каталогизировать тестовую базу.
- `assess-ecosystem`&nbsp;—&nbsp;ограниченное исследование публичных источников, с потолком по бюджету токенов.
- `understand-sut-constraints`&nbsp;—&nbsp;ограничения SUT, которые ломают параллельные тесты.
- `understand-ocarina`&nbsp;—&nbsp;пройтись по документации.

### Выбор (3)

По mtime — никогда по имени файла.

- `pick-screenshots`, `pick-logs`, `pick-reports`.

### Авторство (9)

Каждый выдаёт готовый результат.

- `empiricism`&nbsp;—&nbsp;проверяйте перед кодированием; не перезаписывайте intentional-fail gap-тесты.
- `write-a-probe`&nbsp;—&nbsp;одноразовый скрипт, в gitignore.
- `write-test-strategy`&nbsp;—&nbsp;сгенерировать документ test-strategy из набора (scope, types, таблицы покрытия, дерево цикла, pass/fail, gaps,
  CI-матрица).
- `plan-test-effort`&nbsp;—&nbsp;наивный, «первый проход» плана усилий по тестированию; критичность (critical/major/minor), лёгкий реестр рисков, веса
  S&nbsp;/&nbsp;M&nbsp;/&nbsp;L, открытые вопросы для углублённого прохода.
- `extend-coverage`&nbsp;—&nbsp;расширить покрытие, опираясь на существующие активы.
- `update-frd-and-tests`&nbsp;—&nbsp;протянуть обновление spec во внутрипроектной FRD; вышестоящие системы (Confluence, Jira, …) остаются доступны
  только для чтения.
- `manual-reproduction-guide`&nbsp;—&nbsp;repro, который может выполнить человек.
- `manage-backlog`&nbsp;—&nbsp;`BACKLOG.md`.
- `pr-report`&nbsp;—&nbsp;отчёт с учётом типа PR.

### Рефакторинг (2)

- `refactor-fragmentation`&nbsp;—&nbsp;DRY на усмотрение пользователя.
- `introduce-pom-retries`&nbsp;—&nbsp;повторы внутри POM с разбивкой на два теста (first-try + with-retries).

### Состояние (1)

- `question-state`&nbsp;—&nbsp;опросить окружение, прежде чем доверять результату.

### Настройка (2)

- `setup-environment`&nbsp;—&nbsp;venv, инструменты разработки, набор скиллов Ocarina, скопированный в директорию скиллов Claude Code, пути к
  драйверам в `CLAUDE.local.md`, цикл pre-commit, smoke-проверка раннера.
- `profile-environment`&nbsp;—&nbsp;определяет рамки дозволенного на проекте (доступ к исходникам, зондирование вживую, чувствительность данных,
  конфиденциальность, безопасность, автономия, правки в репозитории) и генерирует дополнение `CLAUDE.profile.md`, которое лишь ужесточает настройки по
  умолчанию и никогда их не ослабляет.

### Запуск (1)

- `propose-visual-review`&nbsp;—&nbsp;перед локальным запуском предлагает выбор: `--not-headless` (смотреть, как браузер отыгрывает сценарий) или
  headless (как в CI). Собирает команду; запускает пользователь.

## Повторяющиеся цепочки

**Набор не зелёный:** `review-report`&nbsp;→&nbsp;`analyse-*`&nbsp;→&nbsp;`write-a-probe`&nbsp;→&nbsp;находка ложится в
`IDENTIFIED_GAPS.md`&nbsp;/&nbsp;FRD /&nbsp;комментарий сценария&nbsp;→&nbsp;probe удаляется.

**Сценарий чёрной шляпы выглядит многообещающе:** `empiricism`&nbsp;→&nbsp;`extend-coverage` (часто intentional-fail).

**Изменения в spec:** `update-frd-and-tests` (сначала FRD, тесты следом). Gap-тесты переосмысляются, а не переворачиваются.

**Нужен новый примитив Ocarina:** сначала `understand-ocarina`, потом писать.

**Собираетесь запустить прогон:** `propose-visual-review` — с интерфейсом (`--not-headless`) или headless (как в CI)? Собирает команду; запускает
пользователь.

## Дисциплина

**Показывайте, а не применяйте.** Навыки выдают результат — решает пользователь.

**Эмпирика, а не утверждения.** Каждое утверждение о SUT — наблюдённое, процитированное, датированное. Ритуальная фраза: _"Fair point, I'm assuming.
Let me verify empirically."_

**Gap-тесты переосмысляют, а не перекрашивают в зелёный.** Инвертируйте утверждение, переименуйте, перенесите строку в strategy-doc, занесите решение
в `IDENTIFIED_GAPS.md`. Одно движение — через `update-frd-and-tests`.

**Эмиссии watcher'ов — только негативные сигналы.** Watcher, выпускающий _"login succeeded"_, нарушает контракт.

**Распределённо — когда дефицит общий.** Если воркеры борются за ограниченный на стороне SUT ресурс (сессии, слоты, квоты), координируйте их через
распределённые примитивы. Иначе worker-local in-memory cache вполне подойдёт — при условии, что ключи не могут столкнуться, а их генерация
потокобезопасна.

**Рамки можно только сужать.** По умолчанию всё открыто, как на демо: чтение исходников, зондирование вживую, публичные учётные данные.
`profile-environment` подстраивает их под конкретный проект, никогда не ослабляя правила безопасности.

**Mtime, а не имя файла.** UUID-суффиксы случайны; `pick-*` сортирует по mtime.

## Чего эта схема не делает

- Не генерирует тесты автономно.
- Не замазывает галлюцинации в CI; сбой запускает `review-report` + `analyse-*`.
- Не переписывает spec; это делает только `update-frd-and-tests` — со строкой ревизии.
- Не запускает активные тесты безопасности. Никогда.

## Открытые ресурсы

- https://mojo-molotov.github.io/ocarina-holy-book/llms.txt
- https://mojo-molotov.github.io/ocarina-holy-book/llms-full.txt
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.md
- https://mojo-molotov.github.io/ocarina-holy-book/CLAUDE.slim.md
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-ru.pdf
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-en.pdf
- https://mojo-molotov.github.io/ocarina-holy-book/ocarina-fr.pdf

<llm-exclude>

---

![Mojo играет на окарине](/assets/content/docs/creatives/mojo-playing-ocarina.png)

<p align="center" class="good-work-mojo-msg"><i>Ого!<br/>Ты здорово его доработал, читатель Mojo.</i></p>

---

<p align="center" class="inspiring-quote">"On Earth and Space, he has all the tricks."</p>

<p align="right" class="inspiring-quote-author">―&nbsp;▒▒█𝚃𝙾𝙿 𝚂𝙴𝙲𝚁█𝚃 //&nbsp;𝚂𝙲𝙸 //&nbsp;𝙽▒▒▒▒𝙾𝙵𝙾𝚁𝙽</p>

</llm-exclude>
