import unusedImports from 'eslint-plugin-unused-imports';
import perfectionist from 'eslint-plugin-perfectionist';
import importX from 'eslint-plugin-import-x';
import tseslint from 'typescript-eslint';
import globals from 'globals';
import js from '@eslint/js';

const ERROR = 'error';
const OFF = 'off';

export default [
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '.wireit/**',
      'typecheck-dist/**',
      'docs/.vitepress/dist/**',
      'docs/.vitepress/cache/**',
      '.commitlintrc.cjs',
      '.lintstagedrc.cjs'
    ]
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      ...perfectionist.configs['recommended-alphabetical'].rules,
      ...perfectionist.configs['recommended-natural'].rules,
      ...perfectionist.configs['recommended-line-length'].rules,

      '@typescript-eslint/no-unused-vars': [ERROR, { ignoreRestSiblings: false, args: 'after-used', vars: 'all' }],
      '@typescript-eslint/consistent-type-imports': [ERROR, { fixStyle: 'separate-type-imports' }],
      'import-x/no-extraneous-dependencies': [OFF, { devDependencies: false }],

      'import-x/consistent-type-specifier-style': [ERROR, 'prefer-top-level'],
      '@typescript-eslint/no-unsafe-declaration-merging': ERROR,
      '@typescript-eslint/no-explicit-any': OFF,
      'unused-imports/no-unused-imports': ERROR,

      'import-x/no-duplicates': ERROR,
      'import-x/first': ERROR,

      'no-unreachable': ERROR,
      'require-await': ERROR,
      'no-eval': ERROR
    },
    languageOptions: {
      parserOptions: {
        tsconfigRootDir: import.meta.dirname,
        projectService: true
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.es2021
      },
      ecmaVersion: 'latest',
      sourceType: 'module'
    },
    plugins: {
      'unused-imports': unusedImports,
      'import-x': importX,
      perfectionist
    }
  }
] as const;
