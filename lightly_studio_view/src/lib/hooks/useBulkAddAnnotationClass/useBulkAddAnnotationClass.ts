import { get } from 'svelte/store';
import { useQueryClient } from '@tanstack/svelte-query';
import type { ClassificationAnnotationsCreated } from '$lib/api/lightly_studio_local';
import {
    readAnnotationCollectionsQueryKey,
    readAnnotationLabelsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    createClassificationAnnotations,
    createClassificationAnnotationsByFilter
} from '$lib/api/lightly_studio_local/sdk.gen';
import { useInvalidateCollectionHierarchyQueries } from '$lib/hooks/useCollection/useCollection';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';
import { useInvalidateEvaluationRunsQueries } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
import { usePostHog } from '$lib/hooks/usePostHog';

interface AddAnnotationClassParams {
    /** Annotation class every selected sample gets. */
    className: string;
    /** Annotation source the new annotations are written to; created lazily backend-side. */
    annotationSource: string;
    selectedSampleIds: Set<string>;
}

export const useBulkAddAnnotationClass = ({
    getCollectionId
}: {
    getCollectionId: () => string;
}) => {
    const client = useQueryClient();
    const { getSelectAllSnapshot } = useGlobalStorage();
    const { trackEvent } = usePostHog();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();
    const invalidateCollectionHierarchyQueries = useInvalidateCollectionHierarchyQueries();

    const refetch = (collectionId: string) => {
        // The grids embed the annotations of every sample, so the class pills need the payload
        // queries refreshed, not just the counts.
        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({ queryKey: useImageAnnotationCountsQueryKey });
        // Annotations can land in a brand-new source and under a brand-new class, both created
        // by name, so refresh the pickers that list them.
        client.invalidateQueries({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: collectionId } })
        });
        client.invalidateQueries({
            queryKey: readAnnotationLabelsQueryKey({ path: { collection_id: collectionId } })
        });
        // A brand-new source is a new child collection, which the navigation menu lists.
        invalidateCollectionHierarchyQueries();
        // Annotation mutations can mark evaluation runs as stale, so refresh the runs list.
        invalidateEvaluationRunsQueries();
    };

    /**
     * Send the selection by filter while it is still an unmodified select-all, so a selection of
     * every sample in a large collection does not travel as a list of IDs. Any manual toggle
     * invalidates the snapshot and falls back to the ID path.
     */
    const requestCreate = (
        collectionId: string,
        { className, annotationSource, selectedSampleIds }: AddAnnotationClassParams
    ) => {
        const snapshot = get(getSelectAllSnapshot(collectionId));
        const isUnmodifiedSelectAll = snapshot != null && snapshot.size === selectedSampleIds.size;
        const body = { class_name: className, annotation_collection_name: annotationSource };

        if (isUnmodifiedSelectAll) {
            return createClassificationAnnotationsByFilter({
                path: { collection_id: collectionId },
                body: { ...body, filter: snapshot.filter },
                throwOnError: true
            });
        }
        return createClassificationAnnotations({
            path: { collection_id: collectionId },
            body: { ...body, sample_ids: [...selectedSampleIds] },
            throwOnError: true
        });
    };

    const addAnnotationClass = async (
        params: AddAnnotationClassParams
    ): Promise<ClassificationAnnotationsCreated> => {
        const collectionId = getCollectionId();
        const { data } = await requestCreate(collectionId, params);
        refetch(collectionId);
        // Shared with the annotation-grid relabel path; the property set names this call site.
        trackEvent('annotations_bulk_labeled', {
            collection_id: collectionId,
            selected_count: params.selectedSampleIds.size,
            created_count: data.created_count,
            skipped_count: data.skipped_count
        });
        return data;
    };

    return { addAnnotationClass };
};
