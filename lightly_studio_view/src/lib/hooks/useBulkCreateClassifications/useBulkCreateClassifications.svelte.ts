import {
    bulkCreateClassifications,
    bulkCreateClassificationsByFilter
} from '$lib/api/lightly_studio_local';
import {
    readAnnotationCollectionsQueryKey,
    readAnnotationLabelsQueryKey,
    readCollectionHierarchyQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    useImageAnnotationCountsQueryKey,
    useInvalidateAnnotationGridQueries,
    useInvalidateEvaluationRunsQueries,
    usePostHog
} from '$lib/hooks';
import { useQueryClient } from '@tanstack/svelte-query';
import { tick } from 'svelte';
import { toast } from 'svelte-sonner';

type BulkCreateClassificationsResult = NonNullable<
    Awaited<ReturnType<typeof bulkCreateClassifications>>['data']
>;

type BulkCreateClassificationsByFilterBody = NonNullable<
    Parameters<typeof bulkCreateClassificationsByFilter>[0]['body']
>;

interface SelectAllSnapshot {
    filter: BulkCreateClassificationsByFilterBody['filter'];
    size: number;
}

interface BulkCreateClassificationsInput {
    collectionId: string;
    selectedIds: Set<string>;
    className: string;
    sourceName: string;
    selectAllSnapshot: SelectAllSnapshot | null;
    rootCollectionId: string;
}

const requestBulkCreate = ({
    collectionId,
    selectedIds,
    className,
    sourceName,
    selectAllSnapshot
}: BulkCreateClassificationsInput) => {
    const body = { class_name: className, annotation_collection_name: sourceName };
    if (selectAllSnapshot && shouldBulkCreateByFilter({ selectAllSnapshot, selectedIds })) {
        return bulkCreateClassificationsByFilter({
            path: { collection_id: collectionId },
            body: { ...body, filter: selectAllSnapshot.filter }
        });
    }
    return bulkCreateClassifications({
        path: { collection_id: collectionId },
        body: { ...body, sample_ids: [...selectedIds] }
    });
};

export const useBulkCreateClassifications = () => {
    const client = useQueryClient();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();
    const { trackEvent } = usePostHog();

    const invalidate = async (collectionId: string, rootCollectionId: string) => {
        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({
            queryKey: readAnnotationLabelsQueryKey({ path: { collection_id: collectionId } })
        });
        client.invalidateQueries({
            queryKey: readCollectionHierarchyQueryKey({ path: { collection_id: rootCollectionId } })
        });
        invalidateEvaluationRunsQueries();

        // The class can land in a source that did not exist before, and the sidebar counts are
        // filtered by the selected sources. The counts query key is static, so a later change
        // to that selection cannot refetch them: refresh the source list first.
        await client.invalidateQueries({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: collectionId } })
        });
        await tick();
        client.invalidateQueries({ queryKey: useImageAnnotationCountsQueryKey });
    };

    const reportSuccess = (
        { collectionId, rootCollectionId, selectedIds }: BulkCreateClassificationsInput,
        result: BulkCreateClassificationsResult
    ) => {
        // Refetch in the background so the caller clears the selection as soon as the write
        // lands, rather than once every panel has caught up.
        void invalidate(collectionId, rootCollectionId);
        trackEvent('annotations_bulk_labeled', {
            collection_id: collectionId,
            selected_count: selectedIds.size,
            created_count: result.created_count,
            skipped_count: result.skipped_count
        });
        toast.success(formatBulkCreateToast(result, selectedIds.size));
    };

    const addClass = async (
        input: BulkCreateClassificationsInput
    ): Promise<BulkCreateClassificationsResult> => {
        const response = await requestBulkCreate(input);

        if (response.error || !response.data) {
            toast.error('Failed to add the annotation class. Please try again.');
            throw response.error ?? new Error('Failed to add the annotation class.');
        }

        reportSuccess(input, response.data);
        return response.data;
    };

    return { addClass };
};

export const formatBulkCreateToast = (
    result: BulkCreateClassificationsResult,
    selectedCount: number
) => {
    if (result.created_count === 0) {
        return `No images changed; all ${selectedCount} already had this annotation class.`;
    }
    if (result.skipped_count > 0) {
        return `Added to ${result.created_count} of ${selectedCount} images; ${result.skipped_count} already had this annotation class.`;
    }
    return `Added the annotation class to ${result.created_count} images.`;
};

interface ShouldBulkCreateByFilterInput {
    selectAllSnapshot: SelectAllSnapshot | null;
    selectedIds: Set<string>;
}

export const shouldBulkCreateByFilter = ({
    selectAllSnapshot,
    selectedIds
}: ShouldBulkCreateByFilterInput) =>
    selectAllSnapshot != null && selectAllSnapshot.size === selectedIds.size;
