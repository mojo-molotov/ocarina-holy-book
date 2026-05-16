import { defineConfig } from 'vitepress';
import path from 'path';
import fs from 'fs';

import { generateSkills } from './plugins/skills';
import { generateLlms } from './plugins/llm';
import { generatePub } from './plugins/pub';
import { blogTheme } from './blog-theme';
import webpConfig from './plugins/webp';

const base = process.env.GITHUB_ACTIONS === 'true' ? '/ocarina-holy-book/' : '/';

export default defineConfig({
  locales: {
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
      title: "Le livre sacré d'Ocarina",
      label: 'Français',
      lang: 'fr'
    }
  },
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
      ...generateLlms(),
      ...generateSkills(),
      ...generatePub(),
      ...(webpConfig.vite!.plugins as any)
    ]
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
