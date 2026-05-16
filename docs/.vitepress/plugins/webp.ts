// PROUDLY vibe-coded using the 'make no mistake' prompt

import type { Plugin } from 'vitepress';

import { optimizeImages } from 'vitepress-plugin-image-optimize';
import { defineConfig } from 'vitepress';
import path from 'path';
import fs from 'fs';

function createWebpDirs(assetsDir: string, webpDir: string): Plugin {
  return {
    buildStart() {
      const walk = (dir: string) => {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
          if (entry.isDirectory()) {
            const relative = path.relative(assetsDir, path.join(dir, entry.name));
            fs.mkdirSync(path.join(webpDir, relative), { recursive: true });
            walk(path.join(dir, entry.name));
          }
        }
      };
      walk(assetsDir);
    },
    name: 'create-webp-dirs'
  };
}

export default defineConfig({
  markdown: {
    config: (md) => {
      md.use(optimizeImages({ lazyLoading: true, srcDir: 'docs', quality: 90 }));
    }
  },
  vite: {
    plugins: [createWebpDirs('docs/public/assets', 'docs/public/webp/assets')]
  }
});
