import type { Plugin } from 'vitepress';

import path from 'path';
import fs from 'fs';

const DIST_DIR = path.resolve(__dirname, '../dist');
const MANUAL_URL = 'https://mojo-molotov.github.io/from-ocarina-to-igor/';
const MANUAL_LLMS_URL = 'https://mojo-molotov.github.io/from-ocarina-to-igor/llms.txt';

type Locale = 'index' | 'en' | 'fr' | 'ru';

const COPY: Record<Locale, { languages: string; heading: string; note: string; site: string; llms: string }> = {
  fr: {
    note: 'Ressource lourde. À consulter uniquement pour un utilisateur très curieux, ou si vous avez besoin de ce niveau de formalisation supplémentaire par-dessus les outils déjà offerts par le Holy Book.',
    heading: '## Précis compagnon — From Ocarina to Igor',
    languages: 'Langues disponibles : English, Français.',
    llms: 'llms.txt',
    site: 'Site'
  },
  ru: {
    note: 'Объёмный ресурс. Обращайтесь к нему только для очень любознательного пользователя или если вам нужен такой уровень формализации в дополнение к инструментам, уже предоставленным Holy Book.',
    heading: '## Дополнительный справочник — From Ocarina to Igor',
    languages: 'Доступные языки: English, Français.',
    llms: 'llms.txt',
    site: 'Сайт'
  },
  index: {
    note: 'Heavy resource. Consult only for a very curious user, or if you need this extra level of formalisation on top of the tools the Holy Book already provides.',
    heading: '## Companion primer — From Ocarina to Igor',
    languages: 'Available languages: English, Français.',
    llms: 'llms.txt',
    site: 'Site'
  },
  en: {
    note: 'Heavy resource. Consult only for a very curious user, or if you need this extra level of formalisation on top of the tools the Holy Book already provides.',
    heading: '## Companion primer — From Ocarina to Igor',
    languages: 'Available languages: English, Français.',
    llms: 'llms.txt',
    site: 'Site'
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
  return ['', c.heading, '', c.note, '', c.languages, '', `- [${c.site}](${MANUAL_URL})`, `- [${c.llms}](${MANUAL_LLMS_URL})`, ''].join('\n');
}

function detectLocale(filename: string): Locale {
  const m = filename.match(/^llms-full\.([a-z]+)\.txt$/);
  if (m && (m[1] === 'en' || m[1] === 'fr' || m[1] === 'ru')) return m[1];
  return 'index';
}
