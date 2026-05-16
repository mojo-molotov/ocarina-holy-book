import type { Plugin } from 'vitepress';

import path from 'path';
import fs from 'fs';

const SKILLS_DIR = path.resolve(__dirname, '../../../ai/skills');
const AI_DIR = path.resolve(__dirname, '../../../ai');
const CLAUDE_FILES = ['CLAUDE.md', 'CLAUDE.slim.md'] as const;
const DIST_DIR = path.resolve(__dirname, '../dist');
const PUBLIC_PREFIX = '/skills';

export function generateSkills(): Plugin[] {
  return [
    {
      closeBundle() {
        if (fs.existsSync(SKILLS_DIR)) {
          const files = collectFiles(SKILLS_DIR);
          copyToPublic(files);
          appendToLlms(files);
        }

        const claudeFiles = CLAUDE_FILES.filter((name) => fs.existsSync(path.join(AI_DIR, name)));
        if (claudeFiles.length > 0) {
          for (const name of claudeFiles) copyClaudeFile(name);
          appendClaudeFilesToLlms(claudeFiles);
        }
      },
      name: 'generate-skills:emit',
      enforce: 'post',
      apply: 'build'
    }
  ];
}

function appendToLlms(files: { abs: string; rel: string }[]) {
  const mdFiles = files.filter((f) => f.rel.endsWith('.md'));

  const indexLines: string[] = ['', '## Skills', ''];
  for (const { rel, abs } of mdFiles) {
    const url = `${PUBLIC_PREFIX}/${rel}`;
    const title = extractTitle(fs.readFileSync(abs, 'utf-8')) ?? rel;
    indexLines.push(`- [${title}](${url})`);
  }
  indexLines.push('');
  const indexBlock = indexLines.join('\n');

  const targets = fs.readdirSync(DIST_DIR).filter((f) => f === 'llms.txt' || /^llms-full(\.[a-z]+)?\.txt$/.test(f));
  for (const name of targets) {
    fs.appendFileSync(path.join(DIST_DIR, name), indexBlock);
  }
}

function appendClaudeFilesToLlms(names: readonly string[]) {
  const lines = ['', '## Claude Context', ''];
  for (const name of names) {
    const title = extractTitle(fs.readFileSync(path.join(AI_DIR, name), 'utf-8')) ?? name;
    lines.push(`- [${title}](/${name})`);
  }
  lines.push('');
  const block = lines.join('\n');

  const targets = fs.readdirSync(DIST_DIR).filter((f) => f === 'llms.txt' || /^llms-full(\.[a-z]+)?\.txt$/.test(f));
  for (const name of targets) {
    fs.appendFileSync(path.join(DIST_DIR, name), block);
  }
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

function copyToPublic(files: { abs: string; rel: string }[]) {
  const dest = path.join(DIST_DIR, 'skills');
  for (const { rel, abs } of files) {
    const target = path.join(dest, rel);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(abs, target);
  }
}

function extractTitle(content: string) {
  const fmName = content.match(/^---\s*[\s\S]*?\bname:\s*(.+?)\s*$[\s\S]*?---/m)?.[1];
  if (fmName) return fmName;
  return content.match(/^#\s+(.+)$/m)?.[1] ?? null;
}

function copyClaudeFile(name: string) {
  const target = path.join(DIST_DIR, name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(path.join(AI_DIR, name), target);
}
