import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
    input: '../lightly_studio/openapi.json',
    output: {
        format: 'prettier',
        lint: 'eslint',
        path: './src/lib/api/lightly_studio_local'
    },
    plugins: [
        '@hey-api/schemas',
        {
            dates: true,
            name: '@hey-api/transformers'
        },
        {
            enums: 'javascript',
            name: '@hey-api/typescript'
        },
        {
            // The base URL is set at runtime from PUBLIC_LIGHTLY_STUDIO_API_URL.
            baseUrl: false,
            name: '@hey-api/client-fetch',
            runtimeConfigPath: './src/lib/api/clientConfig.ts'
        },
        {
            name: '@hey-api/sdk',
            transformer: true
        },
        '@tanstack/svelte-query'
    ]
});
