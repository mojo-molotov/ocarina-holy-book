import type { Theme } from 'vitepress';

import BlogTheme from '@sugarat/theme';
import { h } from 'vue';

import './style.css';
import NotFound from './components/NotFound.vue';

// Color palette
// import './user-theme.css'

const { Layout } = BlogTheme;

export default {
  ...BlogTheme,
  Layout: () =>
    h(Layout!, null, {
      'not-found': () => h(NotFound)
    })
} satisfies Theme;
