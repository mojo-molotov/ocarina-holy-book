import type { Plugin } from 'vitepress';

import path from 'path';
import fs from 'fs';

const PUB_DIR = path.resolve(__dirname, '../../../pub');
const DIST_DIR = path.resolve(__dirname, '../dist');

export function generatePub(): Plugin[] {
  return [
    {
      closeBundle() {
        if (!fs.existsSync(PUB_DIR)) return;

        for (const { abs, rel } of collectFiles(PUB_DIR)) {
          const target = path.join(DIST_DIR, rel);
          fs.mkdirSync(path.dirname(target), { recursive: true });
          fs.copyFileSync(abs, target);
        }
      },
      name: 'generate-pub:emit',
      enforce: 'post',
      apply: 'build'
    }
  ];
}

function collectFiles(root: string): { abs: string; rel: string }[] {
  const out: { abs: string; rel: string }[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const abs = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(abs);
      else if (entry.isFile()) out.push({ rel: path.relative(root, abs).replace(/\\/g, '/'), abs });
    }
  };
  walk(root);
  return out;
}
