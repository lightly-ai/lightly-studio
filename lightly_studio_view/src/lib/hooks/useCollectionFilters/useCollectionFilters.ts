import { derived, toStore } from 'svelte/store';
import { useAnnotationLabels } from '../useAnnotationLabels/useAnnotationLabels';
import { useAnnotationsFilter } from '../useAnnotationsFilter/useAnnotationsFilter';
import { useDimensions } from '../useDimensions/useDimensions';
import {
    createMetadataFilters,
    useMetadataFilters
} from '../useMetadataFilters/useMetadataFilters';
import { useVideoFramesBounds } from '../useVideoFramesBounds/useVideoFramesBounds';
import { useVideoBounds } from '../useVideosBounds/useVideosBounds';
import { useImageFilters } from '../useImageFilters/useImageFilters';
import { useVideoFilters } from '../useVideoFilters/useVideoFilters';

/**
 * Consolidates all filter-related setup for a collection.
 * This includes annotation labels, metadata filters, dimensions, and bounds.
 */
export function useCollectionFilters({ collectionId }: { collectionId: string }) {
    const collectionIdStore = toStore(() => collectionId);

    // Metadata and dimensions
    const { metadataValues } = useMetadataFilters(collectionId);
    const { dimensionsValues } = useDimensions(collectionIdStore);

    // Annotation labels and filters
    const annotationLabelsQuery = useAnnotationLabels({ collectionId: collectionId ?? '' });
    const annotationLabelsData = derived(annotationLabelsQuery, ($query) => $query?.data);

    const {
        annotationFilter: annotationFilterStore,
        annotationFilterRows,
        toggleAnnotationFilterSelection,
        setAnnotationCounts
    } = useAnnotationsFilter({
        annotationLabels: annotationLabelsData
    });

    // Metadata filters
    const metadataFilters = derived(metadataValues, ($metadataValues) =>
        $metadataValues ? createMetadataFilters($metadataValues) : undefined
    );

    // Video bounds
    const { videoFramesBoundsValues } = useVideoFramesBounds();
    const { videoBoundsValues } = useVideoBounds();

    // Plot selection filters
    const { imageFilter: imageFilterFromHook } = useImageFilters();
    const { videoFilter: videoFilterFromHook } = useVideoFilters();
    const plotSelectionImageSampleIds = derived(
        imageFilterFromHook,
        ($imageFilterFromHook) => $imageFilterFromHook?.sample_filter?.sample_ids ?? []
    );
    const plotSelectionVideoSampleIds = derived(
        videoFilterFromHook,
        ($videoFilterFromHook) => $videoFilterFromHook?.sample_filter?.sample_ids ?? []
    );

    return {
        // Annotation filters
        annotationFilterStore,
        annotationFilterRows,
        toggleAnnotationFilterSelection,
        setAnnotationCounts,
        // Metadata and dimensions
        metadataFilters,
        dimensionsValues,
        // Bounds
        videoFramesBoundsValues,
        videoBoundsValues,
        // Plot selections
        plotSelectionImageSampleIds,
        plotSelectionVideoSampleIds
    };
}
