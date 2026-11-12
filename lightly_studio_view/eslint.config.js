// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from 'eslint-plugin-storybook';

import prettier from 'eslint-config-prettier';
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';
import ts from 'typescript-eslint';

export default ts.config(
    js.configs.recommended,
    ...ts.configs.recommended,
    ...svelte.configs['flat/recommended'],
    prettier,
    ...svelte.configs['flat/prettier'],
    {
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.node
            }
        }
    },
    {
        files: ['**/*.svelte'],

        languageOptions: {
            parserOptions: {
                parser: ts.parser
            }
        }
    },
    {
        ignores: [
            'build/',
            '.svelte-kit/',
            'dist/',
            'storybook-static/',
            'test-results/',
            'src/lib/components/ui/',
            'src/lib/api/lightly_studio_local/',
            'src/lib/components/QueryEditor/language/',
            'src/lib/components/QueryEditor/language-server-worker.ts'
        ]
    },
    storybook.configs['flat/recommended'],
    {
        rules: {
            'no-console': ['error', { allow: ['warn', 'error'] }],
            'no-restricted-imports': [
                'error',
                { paths: [{ name: '$app/stores', message: 'Use $app/state.' }] }
            ]
        }
    },
    {
        // The performance tests print their measurements.
        files: ['e2e/**'],
        rules: { 'no-console': 'off' }
    },
    {
        // Legacy files. Remove a file from this list when you convert it to `$app/state`.
        files: [
            'src/lib/components/Operator/OperatorDialog.svelte',
            'src/lib/components/Operator/OperatorsMenu.svelte',
            'src/routes/+error.svelte',
            'src/routes/error.test.ts'
        ],
        rules: { 'no-restricted-imports': 'off' }
    }
);
