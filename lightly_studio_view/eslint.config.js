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
    storybook.configs['flat/recommended']
);
