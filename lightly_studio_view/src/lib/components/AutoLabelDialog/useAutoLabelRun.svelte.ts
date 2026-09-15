import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import type { ImageFilter } from '$lib/api/lightly_studio_local';

interface ModelDescription {
    model_key: string;
    endpoint: string;
    ready: boolean;
    capabilities: string[];
    supported_conditioning: string[];
    classes?: string[] | null;
}

interface BatchRequest {
    collection_id: string;
    filter: ImageFilter | null;
    task: 'object_detection' | 'segmentation';
    targets: { prompt: string; class_name: string }[];
    confidence_threshold: number;
}

interface BatchSummary {
    source_id: string;
    source_name: string;
    annotations_created: number;
    images_processed: number;
    images_skipped: number;
    unmatched_prompts: string[];
}

export function useAutoLabelRun() {
    const queryClient = useQueryClient();
    const description = createQuery(() => ({
        queryKey: ['auto-label-description'],
        staleTime: 0,
        retry: false,
        queryFn: async () => {
            const { data } = await client.get<{ 200: ModelDescription }, unknown, true>({
                url: '/api/annotate/describe',
                throwOnError: true
            });
            return data;
        }
    }));
    const run = createMutation(() => ({
        mutationFn: async (body: BatchRequest) => {
            const { data } = await client.post<{ 200: BatchSummary }, unknown, true>({
                url: '/api/annotate/batch',
                body,
                headers: { 'Content-Type': 'application/json' },
                throwOnError: true
            });
            return data;
        },
        onSuccess: () => queryClient.invalidateQueries()
    }));
    return { description, run };
}

export function autoLabelError(error: unknown): string {
    if (error instanceof Error) return error.message;
    if (
        typeof error === 'object' &&
        error &&
        'detail' in error &&
        typeof error.detail === 'string'
    ) {
        return error.detail;
    }
    return 'The model request failed. Check the model connection and try again.';
}
