import { readAnnotationsWithPayloadInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { client as apiClient } from '$lib/api/lightly_studio_local/client.gen';
import { readAnnotationsWithPayload } from '$lib/api/lightly_studio_local/sdk.gen';
import { readAnnotationsWithPayloadResponseTransformer } from '$lib/api/lightly_studio_local/transformers.gen';
import type {
    AnnotationWithPayloadAndCountView,
    ReadAnnotationsWithPayloadErrors
} from '$lib/api/lightly_studio_local/types.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { toast } from 'svelte-sonner';
import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import { writable } from 'svelte/store';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';

type ReadAnnotationsWithPayloadOptions = Parameters<
    typeof readAnnotationsWithPayloadInfiniteOptions
>[0];

export const useAnnotationsInfinite = (
    getProps: () => Parameters<typeof readAnnotationsWithPayloadInfiniteOptions>[0]
) => {
    const isPending = writable(false);
    const annotations = createInfiniteQuery(() => {
        const props = getProps();
        return {
            ...readAnnotationsWithPayloadInfiniteOptions(props),
            queryFn: async ({ pageParam, signal }) => {
                return readAnnotationsWithPayloadPage({
                    props,
                    cursor: typeof pageParam === 'number' ? pageParam : undefined,
                    signal
                });
            },
            getNextPageParam: (lastPage) => {
                return lastPage.nextCursor || undefined;
            }
        };
    });
    const client = useQueryClient();
    const refresh = () => {
        const options = readAnnotationsWithPayloadInfiniteOptions(getProps());
        client.invalidateQueries({ queryKey: options.queryKey });
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
    };

    // collection_id is stable (from route), evaluate once at construction
    const collection_id = getProps().path.collection_id;
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        collectionId: collection_id
    });

    return {
        annotations,
        refresh,
        isPending,
        updateAnnotations: async (inputs: AnnotationUpdateInput[]) => {
            try {
                isPending.set(true);
                await updateAnnotations(inputs);
                refresh();
                toast.success('Annotations updated successfully');
            } catch (error: unknown) {
                toast.error('Failed to update annotations:' + (error as Error).message);
            } finally {
                isPending.set(false);
            }
        }
    };
};

const readAnnotationsWithPayloadPage = async ({
    props,
    cursor,
    signal
}: {
    props: ReadAnnotationsWithPayloadOptions;
    cursor: number | undefined;
    signal: AbortSignal;
}): Promise<AnnotationWithPayloadAndCountView> => {
    const query = {
        ...props.query,
        cursor
    };
    if (!shouldUseBodyRequest(query)) {
        const { data } = await readAnnotationsWithPayload({
            ...props,
            query,
            signal,
            throwOnError: true
        });
        return data;
    }

    const { data } = await apiClient.post<
        { 200: AnnotationWithPayloadAndCountView },
        ReadAnnotationsWithPayloadErrors,
        true
    >({
        url: '/api/collections/{collection_id}/annotations/payload/list',
        path: props.path,
        body: {
            pagination: {
                cursor: query.cursor ?? 0,
                limit: query.limit ?? 100
            },
            annotation_label_ids: query.annotation_label_ids,
            tag_ids: query.tag_ids,
            sample_ids: query.sample_ids,
            text_embedding: query.text_embedding
        },
        signal,
        throwOnError: true,
        responseTransformer: readAnnotationsWithPayloadResponseTransformer
    });
    return data;
};

const shouldUseBodyRequest = (query: ReadAnnotationsWithPayloadOptions['query']): boolean => {
    return Boolean(
        (query?.sample_ids && query.sample_ids.length > 0) ||
            (query?.text_embedding && query.text_embedding.length > 0)
    );
};
