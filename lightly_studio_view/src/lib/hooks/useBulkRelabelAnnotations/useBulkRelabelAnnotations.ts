import {
    bulkRelabelAnnotations,
    bulkRelabelAnnotationsByFilter
} from '$lib/api/lightly_studio_local';
import { readAnnotationLabelsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    useImageAnnotationCountsQueryKey,
    useInvalidateAnnotationGridQueries,
    useInvalidateEvaluationRunsQueries,
    usePostHog
} from '$lib/hooks';
import { useQueryClient } from '@tanstack/svelte-query';
import { readonly, writable, type Readable } from 'svelte/store';

type BulkRelabelAnnotationsByFilterBody = NonNullable<
    Parameters<typeof bulkRelabelAnnotationsByFilter>[0]['body']
>;

interface SelectAllSnapshot {
    filter: BulkRelabelAnnotationsByFilterBody['filter'];
    size: number;
}

interface BulkRelabelAnnotationsInput {
    collectionId: string;
    selectedIds: Set<string>;
    selectAllSnapshot: SelectAllSnapshot | null;
    labelName: string;
}

interface BulkRelabelAnnotationsResult {
    data?: Awaited<ReturnType<typeof bulkRelabelAnnotations>>['data'];
    error?: unknown;
}

export interface UseBulkRelabelAnnotations {
    relabelAnnotations: (
        input: BulkRelabelAnnotationsInput
    ) => Promise<BulkRelabelAnnotationsResult>;
    isPending: Readable<boolean>;
}

const requestBulkRelabel = ({
    collectionId,
    selectedIds,
    selectAllSnapshot,
    labelName
}: BulkRelabelAnnotationsInput) => {
    // An unmodified select-all is relabeled by its filter, not by a potentially large ID list.
    if (selectAllSnapshot?.size === selectedIds.size) {
        return bulkRelabelAnnotationsByFilter({
            path: { collection_id: collectionId },
            body: { filter: selectAllSnapshot.filter, label_name: labelName }
        });
    }
    return bulkRelabelAnnotations({
        path: { collection_id: collectionId },
        body: { annotation_ids: [...selectedIds], label_name: labelName }
    });
};

export const useBulkRelabelAnnotations = (): UseBulkRelabelAnnotations => {
    const client = useQueryClient();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();
    const { trackEvent } = usePostHog();
    const isPending = writable(false);

    const invalidateQueries = (collectionId: string) => {
        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({ queryKey: useImageAnnotationCountsQueryKey });
        // The relabel creates the label if it does not exist yet.
        client.invalidateQueries({
            queryKey: readAnnotationLabelsQueryKey({ path: { collection_id: collectionId } })
        });
        invalidateEvaluationRunsQueries();
    };

    const relabelAnnotations = async (
        input: BulkRelabelAnnotationsInput
    ): Promise<BulkRelabelAnnotationsResult> => {
        isPending.set(true);
        try {
            const { data, error } = await requestBulkRelabel(input);
            if (data) {
                invalidateQueries(input.collectionId);
                trackEvent('annotations_bulk_labeled', {
                    collection_id: input.collectionId,
                    annotation_count: data.previous_labels.length
                });
            }
            return { data, error };
        } catch (error) {
            return { error };
        } finally {
            isPending.set(false);
        }
    };

    return { relabelAnnotations, isPending: readonly(isPending) };
};
