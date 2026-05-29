import type { Plugin } from 'vitepress';

import path from 'path';
import fs from 'fs';

const DIST_DIR = path.resolve(__dirname, '../dist');

type Locale = 'index' | 'en' | 'fr' | 'ru';

const COPY: Record<Locale, { heading: string; bridge: string; intro: string }> = {
  ru: {
    bridge:
      '- [From Ocarina to Igor](https://mojo-molotov.github.io/from-ocarina-to-igor/): обратная разработка всей экосистемы Ocarina (6 публичных репозиториев) + обоснование решений. Репозитории: `ocarina` (Python-фреймворк; типы Result, Railway-Oriented Programming), `ocarina-example` (канонический e2e-набор), `ocarina-with-ai-example` (набор, написанный с ИИ), `igoristan` (намеренно хаотичный публичный SUT; цель `ocarina-example`), `tests-workers` (бэкенд OTP/координации Vercel Edge; распределённые прогоны), `ocarina-holy-book` (эта документация). Также: CI/CD + философия каждого решения. Назначение: посмотреть шире на *почему*/*как* построен стек, а не только что делает Ocarina. Переходить, когда вопрос выходит за пределы Holy Book к остальной части стека или её обоснованию. Канонический источник: <https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt> (языки: English, Français).',
    intro:
      'Ocarina — одна из частей более широкого стека: ссылки ниже представляют собой **мосты** («bridge docs») — короткие документы в этом репозитории, которые описывают роль каждого соседнего проекта и указывают на его собственную каноническую документацию. **Если вопрос затрагивает поведение соседа, перейдите по мосту к его `llms.txt`; при сомнении спросите пользователя — никогда не пропускайте мост молча.** Holy Book не описывает содержимое соседних проектов (это привело бы к расхождению); его задача — сделать взаимосвязи читаемыми, не более.',
    heading: '## Связанные проекты'
  },
  fr: {
    bridge:
      "- [From Ocarina to Igor](https://mojo-molotov.github.io/from-ocarina-to-igor/) : rétro-ingénierie de tout l'écosystème Ocarina (6 dépôts publics) + raisons de conception. Dépôts : `ocarina` (framework Python ; types Result, Railway-Oriented Programming), `ocarina-example` (suite e2e canonique), `ocarina-with-ai-example` (suite co-écrite IA), `igoristan` (SUT public volontairement chaotique ; cible de `ocarina-example`), `tests-workers` (backend OTP/coordination Vercel Edge ; runs distribués), `ocarina-holy-book` (cette doc). Aussi : CI/CD + philosophie de chaque décision. Usage : zoomer sur *pourquoi*/*comment* la stack a été construite, pas seulement ce que fait Ocarina. À suivre quand une question dépasse le Holy Book vers le reste de la stack ou ses raisons. Canonique : <https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt> (langues : English, Français).",
    intro:
      "Ocarina est une brique d'une stack plus large : les liens ci-dessous sont des **ponts** (« bridge docs ») — courts documents hébergés ici qui décrivent le rôle de chaque projet voisin et renvoient à sa documentation canonique. **Si une question touche le comportement d'un voisin, suivez le pont vers son `llms.txt` ; en cas de doute, demandez à l'utilisateur — ne sautez jamais le pont silencieusement.** Le Holy Book ne décrit pas le contenu des projets voisins (ça divergerait) ; il rend l'interconnexion lisible, point.",
    heading: '## Projets liés'
  },
  index: {
    bridge:
      '- [From Ocarina to Igor](https://mojo-molotov.github.io/from-ocarina-to-igor/): reverse-engineering primer of the whole Ocarina ecosystem (6 public repos) + design rationale. Repos: `ocarina` (Python framework; Result types, Railway-Oriented Programming), `ocarina-example` (canonical e2e suite), `ocarina-with-ai-example` (AI-co-written suite), `igoristan` (intentionally-chaotic public SUT; target of `ocarina-example`), `tests-workers` (Vercel Edge OTP/coordination backend; distributed runs), `ocarina-holy-book` (this doc). Also: CI/CD + philosophy behind each decision. Use: zoom out on *why*/*how* the stack was built, not just what Ocarina does. Follow when a question goes past the Holy Book into the wider stack or its rationale. Canonical: <https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt> (langs: English, Français).',
    intro:
      "Ocarina is one piece of a wider stack: the links below are **bridges** — short docs hosted here that name the role of each neighbouring project and point at its own canonical documentation. **If a question touches a neighbour's behaviour, follow the bridge to its `llms.txt`; when in doubt, ask the user — never skip the bridge silently.** The Holy Book does not describe the content of neighbouring projects (that would diverge); it makes the interconnection legible, nothing more.",
    heading: '## Related projects'
  },
  en: {
    bridge:
      '- [From Ocarina to Igor](https://mojo-molotov.github.io/from-ocarina-to-igor/): reverse-engineering primer of the whole Ocarina ecosystem (6 public repos) + design rationale. Repos: `ocarina` (Python framework; Result types, Railway-Oriented Programming), `ocarina-example` (canonical e2e suite), `ocarina-with-ai-example` (AI-co-written suite), `igoristan` (intentionally-chaotic public SUT; target of `ocarina-example`), `tests-workers` (Vercel Edge OTP/coordination backend; distributed runs), `ocarina-holy-book` (this doc). Also: CI/CD + philosophy behind each decision. Use: zoom out on *why*/*how* the stack was built, not just what Ocarina does. Follow when a question goes past the Holy Book into the wider stack or its rationale. Canonical: <https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt> (langs: English, Français).',
    intro:
      "Ocarina is one piece of a wider stack: the links below are **bridges** — short docs hosted here that name the role of each neighbouring project and point at its own canonical documentation. **If a question touches a neighbour's behaviour, follow the bridge to its `llms.txt`; when in doubt, ask the user — never skip the bridge silently.** The Holy Book does not describe the content of neighbouring projects (that would diverge); it makes the interconnection legible, nothing more.",
    heading: '## Related projects'
  }
};

export function generateManual(): Plugin[] {
  return [
    {
      closeBundle() {
        if (!fs.existsSync(DIST_DIR)) return;
        const targets = fs.readdirSync(DIST_DIR).filter((f) => f === 'llms.txt' || /^llms-full(\.[a-z]+)?\.txt$/.test(f));
        for (const name of targets) {
          const locale = detectLocale(name);
          fs.appendFileSync(path.join(DIST_DIR, name), buildBlock(locale));
        }
      },
      name: 'generate-manual:emit',
      enforce: 'post',
      apply: 'build'
    }
  ];
}

function buildBlock(locale: Locale): string {
  const c = COPY[locale];
  return ['', c.heading, '', c.intro, '', c.bridge, ''].join('\n');
}

const LOCALES = ['en', 'fr', 'ru'] as const;

function detectLocale(filename: string): Locale {
  const m = filename.match(/^llms-full\.([a-z]+)\.txt$/);
  if (m && (LOCALES as readonly string[]).includes(m[1])) return m[1] as Locale;
  return 'index';
}
