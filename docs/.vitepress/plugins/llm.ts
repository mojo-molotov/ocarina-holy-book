// PROUDLY vibe-coded using the 'make no mistake' prompt

import type { Plugin } from 'vitepress';

import path from 'path';
import fs from 'fs';

const LOCALES = ['en', 'fr', 'ru'] as const;
type Locale = (typeof LOCALES)[number];

const IGNORE = ['**/what-is-it.md', '**/first-feedbacks.md', '**/index.md'];

const BASE_URL = 'https://mojo-molotov.github.io/ocarina-holy-book';

const FULL_INTRO: Record<Locale, string> = {
  ru: '# The Ocarina Holy Book — Полная документация (Русский)\n\n> Ocarina: фреймворк браузерного тестирования; один репозиторий более широкого стека. **Связанные проекты** в конце файла = мосты к канонической документации соседних репозиториев. Переходить, когда вопрос выходит за пределы Holy Book.\n\n',
  fr: "# The Ocarina Holy Book — Docs complètes (Français)\n\n> Ocarina : framework de test navigateur ; un dépôt d'une stack plus large. **Projets liés** en fin de fichier = ponts vers la doc canonique des dépôts voisins. À suivre quand une question dépasse le Holy Book.\n\n",
  en: "# The Ocarina Holy Book — Full Docs (English)\n\n> Ocarina: browser-testing framework; one repo in a wider stack. **Related projects** at end = bridges to neighbouring repos' canonical docs. Follow when a question goes past the Holy Book.\n\n"
};

export function generateLlms(): Plugin[] {
  const mdFiles = new Map<string, { content: string; url: string }>();

  return [
    {
      transform(code, id) {
        if (!id.endsWith('.md')) return;

        if (!IGNORE.some((p) => id.includes(p.replace('**/', '')))) {
          const url = mdToUrl(id);
          mdFiles.set(id, { content: strip(code), url });
        }

        return code.replace(/<\/?llm-exclude>/g, '');
      },
      name: 'generate-llms:collect',
      enforce: 'pre',
      apply: 'build'
    },
    {
      closeBundle() {
        const distDir = path.resolve(__dirname, '../dist');
        const byLocale = groupByLocale(mdFiles);

        const activeLocales = LOCALES.filter((l) => byLocale[l].length > 0);

        for (const locale of activeLocales) {
          const blocks = byLocale[locale].map(({ content, url }) => `---\nurl: ${url}\n---\n\n${content.trim()}\n\n`);
          fs.writeFileSync(path.join(distDir, `llms-full.${locale}.txt`), FULL_INTRO[locale] + blocks.join(''));
        }

        const indexLines = [
          '# The Ocarina Holy Book - LLMs Full Documentation',
          '',
          "> Ocarina is a browser-testing framework, and one piece of a wider stack alongside sibling projects. This file is an index of this book's full-text docs by language; for the canonical description of neighbouring projects, follow the bridges under **Related projects** at the bottom.",
          '',
          '## Languages',
          ...activeLocales.map(
            (l) => `- ${l === 'en' ? 'English' : l === 'fr' ? 'Français' : l === 'ru' ? 'Русский' : l}: ${BASE_URL}/llms-full.${l}.txt`
          ),
          ''
        ];
        fs.writeFileSync(path.join(distDir, 'llms-full.txt'), indexLines.join('\n'));

        const lines: string[] = [
          '# The Ocarina Holy Book',
          '',
          "> Ocarina is a browser-testing framework, and one piece of a wider stack alongside sibling projects. This file lists this book's pages; the **Related projects** section at the bottom links bridges to the neighbouring repos' canonical docs.",
          ''
        ];
        for (const locale of activeLocales) {
          lines.push(`## ${locale === 'en' ? 'English' : locale === 'fr' ? 'Français' : locale === 'ru' ? 'Русский' : locale}`);
          for (const { content, url } of byLocale[locale]) {
            const title = extractTitle(content) ?? url;
            lines.push(`- [${title}](${url})`);
          }
          lines.push('');
        }

        const llmsTxtPath = path.join(distDir, 'llms.txt');
        if (fs.existsSync(llmsTxtPath) && fs.readFileSync(llmsTxtPath, 'utf-8') === lines.join('\n')) return;

        fs.writeFileSync(llmsTxtPath, lines.join('\n'));
      },
      name: 'generate-llms:emit',
      enforce: 'post',
      apply: 'build'
    }
  ];
}

const createLocaleMap = <T>(factory: () => T): Record<Locale, T> => LOCALES.reduce((acc, l) => ({ ...acc, [l]: factory() }), {} as Record<Locale, T>);

function groupByLocale(files: Map<string, { content: string; url: string }>) {
  const result = createLocaleMap<{ content: string; url: string }[]>(() => []);
  for (const { content, url } of files.values()) {
    const locale = LOCALES.find((l) => url.startsWith(`${BASE_URL}/${l}/`)) ?? 'en';
    result[locale].push({ content, url });
  }
  return result;
}

function strip(content: string) {
  return content
    .replace(/^---[\s\S]*?---\n?/, '')
    .replace(/description:[\s\S]*?---/g, '---')
    .replace(/<llm-exclude>[\s\S]*?<\/llm-exclude>/g, '');
}

function mdToUrl(id: string) {
  const docsDir = path.resolve(__dirname, '../..');
  const rel = path.relative(docsDir, id).replace(/\.md$/, '').replace(/\\/g, '/');
  return `${BASE_URL}/${rel}`;
}

function extractTitle(content: string) {
  return content.match(/^#\s+(.+)$/m)?.[1] ?? null;
}
