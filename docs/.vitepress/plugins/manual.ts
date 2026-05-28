import type { Plugin } from 'vitepress';

import path from 'path';
import fs from 'fs';

const DIST_DIR = path.resolve(__dirname, '../dist');

type Locale = 'index' | 'en' | 'fr' | 'ru';

const COPY: Record<Locale, { heading: string; bridge: string; intro: string }> = {
  fr: {
    intro:
      "Ocarina est une brique d'une stack plus large&nbsp;: les liens ci-dessous sont des **ponts** (« bridge docs ») — courts documents hébergés ici qui décrivent le rôle de chaque projet voisin et renvoient à sa documentation canonique. **Si une question touche le comportement d'un voisin, suivez le pont vers son `llms.txt`&nbsp;; en cas de doute, demandez à l'utilisateur — ne sautez jamais le pont silencieusement.** Le Holy Book ne décrit pas le contenu des projets voisins (ça divergerait)&nbsp;; il rend l'interconnexion lisible, point.",
    bridge:
      "- [From Ocarina to Igor](https://mojo-molotov.github.io/from-ocarina-to-igor/)&nbsp;: bridge doc — explique le rôle d'Igor dans la stack Ocarina et comment le framework de test s'y branche. Pour la description canonique d'Igor lui-même, voir <https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt> (langues disponibles&nbsp;: English, Français).",
    heading: '## Projets liés'
  },
  ru: {
    intro:
      'Ocarina — одна из частей более широкой стека: ссылки ниже представляют собой **мосты** («bridge docs») — короткие документы в этом репозитории, которые описывают роль каждого соседнего проекта и указывают на его собственную каноническую документацию. **Если вопрос затрагивает поведение соседа, перейдите по мосту к его `llms.txt`; при сомнении спросите пользователя — никогда не пропускайте мост молча.** Holy Book не описывает содержимое соседних проектов (это привело бы к расхождению); его задача — сделать взаимосвязи читаемыми, не более.',
    bridge:
      '- [From Ocarina to Igor](https://mojo-molotov.github.io/from-ocarina-to-igor/): bridge doc — описывает роль Igor в стеке Ocarina и то, как фреймворк тестирования к нему подключается. Каноническое описание самого Igor см. в <https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt> (доступные языки: English, Français).',
    heading: '## Связанные проекты'
  },
  index: {
    intro:
      "Ocarina is one piece of a wider stack: the links below are **bridges** — short docs hosted here that name the role of each neighbouring project and point at its own canonical documentation. **If a question touches a neighbour's behaviour, follow the bridge to its `llms.txt`; when in doubt, ask the user — never skip the bridge silently.** The Holy Book does not describe the content of neighbouring projects (that would diverge); it makes the interconnection legible, nothing more.",
    bridge:
      "- [From Ocarina to Igor](https://mojo-molotov.github.io/from-ocarina-to-igor/): bridge doc — explains Igor's role in the Ocarina stack and how the test framework plugs into it. For the canonical description of Igor itself, see <https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt> (available languages: English, Français).",
    heading: '## Related projects'
  },
  en: {
    intro:
      "Ocarina is one piece of a wider stack: the links below are **bridges** — short docs hosted here that name the role of each neighbouring project and point at its own canonical documentation. **If a question touches a neighbour's behaviour, follow the bridge to its `llms.txt`; when in doubt, ask the user — never skip the bridge silently.** The Holy Book does not describe the content of neighbouring projects (that would diverge); it makes the interconnection legible, nothing more.",
    bridge:
      "- [From Ocarina to Igor](https://mojo-molotov.github.io/from-ocarina-to-igor/): bridge doc — explains Igor's role in the Ocarina stack and how the test framework plugs into it. For the canonical description of Igor itself, see <https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt> (available languages: English, Français).",
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
