import { defineConfig } from 'vitepress';
import path from 'path';
import fs from 'fs';

import { generateSkills } from './plugins/skills';
import { generateManual } from './plugins/manual';
import { generateLlms } from './plugins/llm';
import { generatePub } from './plugins/pub';
import { blogTheme } from './blog-theme';
import webpConfig from './plugins/webp';

const base = process.env.GITHUB_ACTIONS === 'true' ? '/ocarina-holy-book/' : '/';

export default defineConfig({
  vite: {
    plugins: [
      {
        load(id) {
          if (id.includes('@sugarat/theme') && id.includes('Pagination.vue')) {
            return fs.readFileSync(path.resolve(__dirname, 'theme/components/Pagination.vue'), 'utf-8');
          }
          if (id.includes('@sugarat/theme') && id.includes('BlogHomeBanner.vue')) {
            return fs.readFileSync(path.resolve(__dirname, 'theme/components/BlogHomeBanner.vue'), 'utf-8');
          }
        },
        name: 'patch-sugarat-components'
      },
      {
        config(config: any) {
          const blog = config?.vitepress?.site?.themeConfig?.blog;
          const siteLocales = config?.vitepress?.site?.locales;
          if (!blog?.locales || !siteLocales) return;

          const localeKeys = Object.keys(siteLocales);
          const nonRoot = localeKeys.filter((k) => k !== 'root');
          const inLocale = (route: string, k: string) => route === `/${k}` || route.startsWith(`/${k}/`);

          // The buggy filter is mutually exclusive, so unioning the per-locale lists
          // reconstructs the full set (blog.pagesData is absent in production builds).
          const all = new Map<string, any>();
          for (const k of localeKeys) {
            for (const page of blog.locales[k]?.pagesData ?? []) {
              all.set(page.route, page);
            }
          }
          const pages = [...all.values()];

          for (const k of localeKeys) {
            if (!blog.locales[k]) blog.locales[k] = {};
            blog.locales[k].pagesData = pages.filter((v) => (k === 'root' ? !nonRoot.some((nk) => inLocale(v.route, nk)) : inLocale(v.route, k)));
          }
        },
        // @sugarat/theme buckets articles into locales with `route.startsWith('/${k}')`
        // (no trailing slash), so a root-locale article whose slug starts with a locale
        // key — e.g. `from-ocarina-to-igor` starts with `fr` — is misfiled into that
        // locale and dropped from English. Re-bucket with an exact `/${k}` or `/${k}/`
        // match after the theme's `config` hook has run.
        name: 'fix-sugarat-locale-prefix-match',
        enforce: 'post'
      },
      ...generateLlms(),
      ...generateSkills(),
      ...generateManual(),
      ...generatePub(),
      ...(webpConfig.vite!.plugins as any)
    ]
  },
  locales: {
    ru: {
      themeConfig: {
        outline: {
          label: 'Оглавление',
          level: [2, 3]
        },
        skipToContentLabel: 'Перейти к содержанию',
        lastUpdatedText: 'Последнее обновление:',
        returnToTopLabel: 'Вернуться вверх',
        sidebarMenuLabel: 'Смотрите также'
      },
      description: 'Ocarina — это автоматизированный фреймворк Игоря для тестирования веб-браузеров.',
      title: 'Священная Книга Ocarina',
      label: 'Русский',
      lang: 'ru'
    },
    fr: {
      themeConfig: {
        outline: {
          label: 'Sommaire',
          level: [2, 3]
        },
        returnToTopLabel: 'Retour en haut de page',
        lastUpdatedText: 'Dernière mise à jour :',
        skipToContentLabel: 'Passer au contenu',
        sidebarMenuLabel: 'Voir aussi'
      },
      description: "Ocarina est le framework de test de navigateur web automatisé d'Igor.",
      title: "Le livre sacré d'Ocarina",
      label: 'Français',
      lang: 'fr'
    },
    root: {
      themeConfig: {
        outline: {
          label: 'Table of content'
        },
        skipToContentLabel: 'Skip to content',
        sidebarMenuLabel: 'Related articles',
        returnToTopLabel: 'Return to top',
        lastUpdatedText: 'Last update:'
      },
      description: "Ocarina is Igor's automated web browser testing framework.",
      title: 'The Ocarina Holy Book',
      label: 'English',
      lang: 'en'
    }
  },
  themeConfig: {
    socialLinks: [
      {
        link: 'https://github.com/mojo-molotov/ocarina',
        icon: 'github'
      }
    ],
    outline: {
      level: [2, 3]
    },
    logo: '/logo.png'
  },

  markdown: {
    config: (md) => {
      webpConfig.markdown!.config!(md); // ← délègue à webp.ts
    }
  },
  sitemap: {
    hostname: 'http://mojo-molotov.github.io/ocarina-holy-book/'
  },
  head: [['link', { href: `${base}favicon.ico`, rel: 'icon' }]],

  extends: blogTheme,
  lang: 'en',
  base
});
