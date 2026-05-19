---
sticky: 1
description: Привет, это я, твой новый лучший друг!

date: 2026-05-16

head:
  - - meta
    - property: og:image
      content: http://mojo-molotov.github.io/ocarina-holy-book/assets/content/docs/creatives/mojo-playing-ocarina.png
---

# Использование Ocarina с AI

Рабочая конфигурация: полный цикл тестирования, построенный рядом с Claude Code и Ocarina, против общедоступной демонстрации Katalon CURA.

[📖 Получите пример AI в качестве справки.](https://github.com/mojo-molotov/ocarina-with-ai-example)

## Три духовных камня

1. `CLAUDE.md` в корне проекта.
2. `skills/` с одним `<name>/SKILL.md` для каждой процедуры.
3. Правило проверки: каждое утверждение SUT исходит из наблюдения (probe, `gh api`, `curl -v`), никогда из вывода.

## `CLAUDE.md`

Два варианта. `CLAUDE.md` полный (правила + макет проекта, иерархия, соглашения, форма CI, шаблон PR). `CLAUDE.slim.md` только правила. Slim когда
контекст тяжёлый; полный для onboarding и обзоров. Полный выигрывает при разногласии.

Шаги Onboarding (venv, `pip install`, `ruff` / `mypy` / `pre-commit`, runner smoke-check) находятся в `setup-environment`.

Правила:

**Тестирование безопасности функционально и статично, никогда не активно.** Нет полезных нагрузок, нет разработанных запросов, нет манипуляции DOM
DevTools. Сценарии чёрных шляп проходят через обычный пользовательский интерфейс.

**Используйте константы.** Именованные значения не встроены.

**Наборы данных — это решения людей.** Предложение не работает.

**Проверьте поведение SUT эмпирически.** Probe, `gh api`, или `curl -v`. Никогда не вывод. Переделайте каждый раз: probe отвечает только за то, что он
работал; предыдущий диагноз только для этого запуска.

Каждое правило несёт однострочный "_почему_".

## `skills/`

Один файл Markdown для каждого навыка, YAML frontmatter + тело. Девять семейств.

### Обзор (13)

Статические чтения; поверхностные находки.

- `review-spec-gaps` — вопросы уточнения на FRD.
- `review-watcher-misuse` — `watcher.report(...)` против соглашения только-отрицательное.
- `review-compartmentalisation-leaks` — URLs, selectors, волшебные числа не на месте.
- `review-dead-code` — неиспользуемые connectors / POMs / сценарии / suites / фрагменты / константы; для каждой находки: удалить, инкубировать
  (`<source-root>/incubator/`, дерево зависимости сохранено), или хранить.
- `review-report` — классифицировать каждый FAIL / SKIP для одного запуска.
- Плюс: `review-type-ignore`, `review-match-candidates`, `review-unverified-transitions`, `review-submit-dispatchers`, `review-comment-drift`,
  `review-suite-stability`, `review-intent-collisions`, `review-watcher-emissions`.

### Анализ (4)

- `analyse-flakiness` — расширить сеть transient-error; хронические смерти — это реальные flakes.
- `analyse-fixture-flakiness` — инструмент setup/teardown; поверхностная перекрёстная контаминация тестов.
- `analyse-watcher-flakiness` — с/без каждого watcher, sweep интервала.
- `analyse-screenshot-flakiness` — группировка по `(test, step, browser)`, заметить различия.

### Чёрная шляпа (6)

- `business-attack-ideation` — сбрось продукт.
- `incoherence-attack-ideation` — каждый шаг легален, набор невозможен.
- `persistence-attack-ideation` — повторные повторы на заблокированных действиях.
- `permission-appropriateness-audit` — уместна ли сама модель доступа?
- `bfcache-exposure-ideation` — BFCache атаки.
- `lateral-resource-ideation` — IDOR через адресную строку только.

### Понимание (4)

- `assess-test-base` — каталог набора.
- `assess-ecosystem` — ограниченные общественные исследования, бюджет токенов закрыт.
- `understand-sut-constraints` — SUT границы, которые разрушают параллельные тесты.
- `understand-ocarina` — пройдите документы.

### Выбор (3)

По mtime, никогда имени файла.

- `pick-screenshots`, `pick-logs`, `pick-reports`.

### Автор (8)

Каждый производит готовый результат.

- `empiricism` — проверьте перед кодированием; не перезаписывайте intentional-fail gap тесты.
- `write-a-probe` — одноразовый скрипт, gitignored.
- `write-test-strategy` — генерируйте документ test-strategy из набора (scope, types, таблицы покрытия, дерево цикла, pass/fail, gaps, CI матрица).
- `extend-coverage` — расширьте покрытие из существующих активов.
- `update-frd-and-tests` — распространите обновление spec.
- `manual-reproduction-guide` — человеко-запускаемый repro.
- `manage-backlog` — `BACKLOG.md`.
- `pr-report` — PR-type-aware отчет.

### Рефакторинг (2)

- `refactor-fragmentation` — DRY по предпочтению пользователя.
- `introduce-pom-retries` — POM-internal повторы с разбивкой на два теста (first-try + with-retries).

### Состояние (1)

- `question-state` — опросить окружение, прежде чем доверять результату.

### Настройка (1)

- `setup-environment` — venv, dev tooling, набор скиллов Ocarina, скопированный в директорию скиллов Claude Code, пути драйвера в `CLAUDE.local.md`,
  pre-commit loop, runner smoke-check.

### Запуск (1)

- `propose-visual-review` — перед локальным запуском предлагает `--not-headless` (наблюдать, как браузер отыгрывает сценарий) против headless (в форме
  CI). Составляет команду; пользователь запускает.

## Повторяющиеся цепи

**Suite не зелёная:** `review-report` → `analyse-*` → `write-a-probe` → находка попадает в `IDENTIFIED_GAPS.md` / FRD / комментарий сценария → probe
удалён.

**Сценарий чёрной шляпы выглядит многообещающе:** `empiricism` → `extend-coverage` (часто intentional-fail).

**Изменения Spec:** `update-frd-and-tests` (FRD первый, тесты следуют). Gap тесты переделаны, не перевёрнуты.

**Нужен новый примитив Ocarina:** сначала `understand-ocarina`, затем написание.

## Дисциплина

**Показывайте, не применяйте.** Навыки производят; пользователь решает.

**Эмпирический, не утверждающий.** Каждое утверждение SUT наблюдается, процитировано, датировано. Ритуальная фраза: _"Fair point, I'm assuming. Let me
verify empirically."_

**Gap-тесты переделаны, не перекрашены в зелёный.** Инвертируйте утверждение, переименуйте, переместите строку strategy-doc, логируйте разрешение в
`IDENTIFIED_GAPS.md`. Одно движение через `update-frd-and-tests`.

**Watcher emissions только отрицательные сигналы.** Watcher, выпускающий _"login succeeded"_ разрывает контракт.

**Распределённо когда нехватка распределённая.** Если рабочие состязаются на SUT-ограниченном ресурсе (сессии, слоты, квоты), координируйте через
распределённые примитивы. Иначе worker-local in-memory cache в порядке — при условии, что ключи не могут столкнуться и генерирование потокобезопасно.

**Mtime, не имя файла.** UUID суффиксы случайны; `pick-*` сортирует по mtime.

## Чем эта настройка не является

- Не генерирует тесты автономно.
- Не латает галлюцинации в CI; отказ запускает `review-report` + `analyse-*`.
- Не переписывает spec; только `update-frd-and-tests` делает, с линией пересмотра.
- Не запускает активные тесты безопасности. Никогда.

## Выставленные ресурсы

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

<p align="right" class="inspiring-quote-author">― ▒▒█𝚃𝙾𝙿 𝚂𝙴𝙲𝚁█𝚃 // 𝚂𝙲𝙸 // 𝙽▒▒▒▒𝙾𝙵𝙾𝚁𝙽</p>

</llm-exclude>
