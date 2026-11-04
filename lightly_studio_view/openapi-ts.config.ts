import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
    input: '../lightly_studio/openapi.json',
    output: './src/lib/api/lightly_studio_local',
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
        {
            name: '@tanstack/svelte-query',
            $hooks: {
                operations: {
                    // Many POST endpoints only read data, so generate query options for them too.
                    getKind: (operation) =>
                        operation.method === 'post' ? ['query', 'mutation'] : undefined
                }
            }
        }
    ]
});
