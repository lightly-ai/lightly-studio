import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
    input: '../lightly_studio/openapi.json',
    output: {
        path: './src/lib/api/lightly_studio_local',
        postProcess: ['prettier']
    },
    parser: {
        hooks: {
            operations: {
                // Keep query options for POST operations, which >=0.82 generates only as mutations.
                isQuery: (operation) => (operation.method === 'post' ? true : undefined)
            }
        }
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
            runtimeConfigPath: './src/lib/api/clientConfig'
        },
        {
            name: '@hey-api/sdk',
            transformer: true
        },
        '@tanstack/svelte-query'
    ]
});
