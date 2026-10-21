import {
    bulkDeleteAnnotations,
    bulkDeleteAnnotationsByFilter
} from '$lib/api/lightly_studio_local';
import {
    readAnnotationCollectionsQueryKey,
    readAnnotationLabelsQueryKey,
    readCollectionHierarchyQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    useImageAnnotationCountsQueryKey,
    useInvalidateAnnotationGridQueries,
    useInvalidateEvaluationRunsQueries
} from '$lib/hooks';
import { useQueryClient } from '@tanstack/svelte-query';
import { readonly, writable, type Readable } from 'svelte/store';

type BulkDeleteAnnotationsByFilterBody = NonNullable<
    Parameters<typeof bulkDeleteAnnotationsByFilter>[0]['body']
>;

interface SelectAllSnapshot {
    filter: BulkDeleteAnnotationsByFilterBody['filter'];
    size: number;
}

interface BulkDeleteAnnotationsInput {
    collectionId: string;
    rootCollectionId: string;
    selectedIds: Set<string>;
    selectAllSnapshot: SelectAllSnapshot | null;
}

type BulkDeleteAnnotationsResult = { ok: true; deletedCount: number } | { ok: false };

export interface UseBulkDeleteAnnotations {
    deleteAnnotations: (input: BulkDeleteAnnotationsInput) => Promise<BulkDeleteAnnotationsResult>;
    isPending: Readable<boolean>;
}

const requestBulkDelete = ({
    collectionId,
    selectedIds,
    selectAllSnapshot
}: BulkDeleteAnnotationsInput) => {
    // An unmodified select-all is deleted by its filter, not by a potentially large ID list.
    if (selectAllSnapshot?.size === selectedIds.size) {
        return bulkDeleteAnnotationsByFilter({
            path: { collection_id: collectionId },
            body: { filter: selectAllSnapshot.filter }
        });
    }
    return bulkDeleteAnnotations({
        path: { collection_id: collectionId },
        body: { annotation_ids: [...selectedIds] }
    });
};

export const useBulkDeleteAnnotations = (): UseBulkDeleteAnnotations => {
    const client = useQueryClient();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();
    const isPending = writable(false);

    const invalidateQueries = ({ collectionId, rootCollectionId }: BulkDeleteAnnotationsInput) => {
        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({ queryKey: useImageAnnotationCountsQueryKey });
        client.invalidateQueries({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: collectionId } })
        });
        client.invalidateQueries({
            queryKey: readAnnotationLabelsQueryKey({ path: { collection_id: collectionId } })
        });
        client.invalidateQueries({
            queryKey: readCollectionHierarchyQueryKey({ path: { collection_id: rootCollectionId } })
        });
        invalidateEvaluationRunsQueries();
    };

    const deleteAnnotations = async (
        input: BulkDeleteAnnotationsInput
    ): Promise<BulkDeleteAnnotationsResult> => {
        isPending.set(true);
        try {
            const { data } = await requestBulkDelete(input);
            if (!data) {
                return { ok: false };
            }
            invalidateQueries(input);
            return { ok: true, deletedCount: data.deleted_count };
        } catch {
            return { ok: false };
        } finally {
            isPending.set(false);
        }
    };

    return { deleteAnnotations, isPending: readonly(isPending) };
};
