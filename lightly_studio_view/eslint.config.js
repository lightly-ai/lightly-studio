// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from 'eslint-plugin-storybook';

import prettier from 'eslint-config-prettier';
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';
import ts from 'typescript-eslint';
import svelteConfig from './svelte.config.js';

export default ts.config(
    js.configs.recommended,
    ...ts.configs.recommended,
    ...svelte.configs.recommended,
    prettier,
    ...svelte.configs.prettier,
    {
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.node
            }
        }
    },
    {
        files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],

        languageOptions: {
            parserOptions: {
                parser: ts.parser,
                svelteConfig
            }
        }
    },
    {
        rules: {
            '@typescript-eslint/no-restricted-imports': [
                'error',
                {
                    paths: [
                        {
                            name: '@lucide/svelte',
                            message:
                                "Import each icon from '@lucide/svelte/icons/<name>'. The root entry loads all icons and slows down tests.",
                            allowTypeImports: true
                        }
                    ]
                }
            ]
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
        // eslint-plugin-svelte 3 enables these rules. Enable them after we fix the findings.
        rules: {
            'svelte/no-dom-manipulating': 'off',
            'svelte/no-useless-children-snippet': 'off',
            'svelte/prefer-writable-derived': 'off',
            'svelte/valid-prop-names-in-kit-pages': 'off',
            // These rules find runtime bugs. Show the findings in new code.
            'svelte/no-navigation-without-resolve': 'warn',
            'svelte/prefer-svelte-reactivity': 'warn',
            'svelte/require-each-key': 'warn'
        }
    },
    {
        // The performance tests print their measurements.
        files: ['e2e/**'],
        rules: { 'no-console': 'off' }
    }
);
