import type {
    BulkCreateClassificationsResult,
    TagByFilterBody
} from '$lib/api/lightly_studio_local';
import {
    bulkCreateClassifications,
    bulkCreateClassificationsByFilter
} from '$lib/api/lightly_studio_local';
import {
    readAnnotationCollectionsQueryKey,
    readAnnotationLabelsQueryKey,
    readCollectionHierarchyQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { useInvalidateEvaluationRunsQueries } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
import { usePostHog } from '$lib/hooks';
import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';

type SelectAllSnapshot = { filter: TagByFilterBody['filter']; size: number };

type BulkCreateClassificationsInput = {
    collectionId: string;
    selectedIds: Set<string>;
    className: string;
    sourceName: string;
    selectAllSnapshot: SelectAllSnapshot | null;
    rootCollectionId: string;
};

export const useBulkCreateClassifications = () => {
    const client = useQueryClient();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();
    const { trackEvent } = usePostHog();

    const invalidate = (collectionId: string, rootCollectionId: string) => {
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

    const addClass = async ({
        collectionId,
        selectedIds,
        className,
        sourceName,
        selectAllSnapshot,
        rootCollectionId
    }: BulkCreateClassificationsInput): Promise<BulkCreateClassificationsResult> => {
        const selectedCount = selectedIds.size;
        const isUnmodifiedSelectAll = shouldBulkCreateByFilter({
            selectAllSnapshot,
            selectedIds
        });
        const response =
            isUnmodifiedSelectAll && selectAllSnapshot
                ? await bulkCreateClassificationsByFilter({
                      path: { collection_id: collectionId },
                      body: {
                          filter: selectAllSnapshot.filter,
                          class_name: className,
                          annotation_collection_name: sourceName
                      }
                  })
                : await bulkCreateClassifications({
                      path: { collection_id: collectionId },
                      body: {
                          sample_ids: [...selectedIds],
                          class_name: className,
                          annotation_collection_name: sourceName
                      }
                  });

        if (response.error || !response.data) {
            toast.error('Failed to add the class. Please try again.');
            throw response.error ?? new Error('Failed to add the class.');
        }

        invalidate(collectionId, rootCollectionId);
        trackEvent('annotations_bulk_labeled', {
            collection_id: collectionId,
            selected_count: selectedCount,
            created_count: response.data.created_count,
            skipped_count: response.data.skipped_count
        });
        toast.success(formatBulkCreateToast(response.data, selectedCount));
        return response.data;
    };

    return { addClass };
};

export const formatBulkCreateToast = (
    result: BulkCreateClassificationsResult,
    selectedCount: number
) => {
    if (result.created_count === 0) {
        return `No images changed; all ${selectedCount} already had this class.`;
    }
    if (result.skipped_count > 0) {
        return `Added to ${result.created_count} of ${selectedCount} images; ${result.skipped_count} already had this class.`;
    }
    return `Added the class to ${result.created_count} images.`;
};

export const shouldBulkCreateByFilter = ({
    selectAllSnapshot,
    selectedIds
}: {
    selectAllSnapshot: SelectAllSnapshot | null;
    selectedIds: Set<string>;
}) => selectAllSnapshot != null && selectAllSnapshot.size === selectedIds.size;
