import { defineConfig } from '@hey-api/openapi-ts';

// POST operations that only read data. Since 0.82, POST operations get only mutation options.
const READ_ONLY_POST_OPERATIONS = new Set([
    'count_image_annotations_by_collection',
    'count_image_annotations_by_sample_tags',
    'count_video_frame_annotations',
    'count_video_frame_annotations_by_video_collection',
    'export_collection_scene_update_options',
    'get_2d_embeddings',
    'get_adjacent_samples',
    'get_all_frames',
    'get_all_groups',
    'get_all_videos',
    'get_image_histograms',
    'get_metadata_histograms',
    'get_metadata_value_counts',
    'list_mcap_sequences',
    'read_samples'
]);

const isSuccessStatus = (status: string) => status.startsWith('2');

export default defineConfig({
    input: '../lightly_studio/openapi.json',
    output: {
        path: './src/lib/api/lightly_studio_local',
        postProcess: ['prettier']
    },
    parser: {
        hooks: {
            operations: {
                isQuery: (operation) =>
                    READ_ONLY_POST_OPERATIONS.has(operation.operationId ?? '') || undefined
            }
        },
        patch: {
            // The client interceptor turns every HTTP error into an `ApiError`. Without the error
            // responses, the query options use the TanStack Query default error type `Error`.
            operations: (_method, _path, operation) => {
                const responses = operation.responses ?? {};
                for (const status of Object.keys(responses)) {
                    if (!isSuccessStatus(status)) delete responses[status];
                }
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
