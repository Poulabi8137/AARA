import tseslint from 'typescript-eslint'

export default tseslint.config(
  {
    ignores: [
      '.next/',
      'backend/',
      'deployment/',
      'load-testing/',
      'scripts/',
      'public/',
      'docs/',
      'screenshots/',
      'node_modules/',
    ],
  },
  {
    files: ['app/**/*.ts', 'app/**/*.tsx', 'components/**/*.ts', 'components/**/*.tsx', 'lib/**/*.ts', 'lib/**/*.tsx', 'proxy.ts'],
    extends: [
      ...tseslint.configs.recommended,
    ],
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-console': 'warn',
    },
  },
)
