import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import globals from 'globals';
import ts from 'typescript-eslint';

export default ts.config(
    js.configs.recommended,
    ...ts.configs.recommended,
    prettier,
    {
        languageOptions: {
            globals: {
                ...globals.node
            }
        }
    },
    {
        ignores: ['node_modules/']
    }
);
