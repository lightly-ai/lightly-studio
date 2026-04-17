import { derived, get } from 'svelte/store';
import { useVideoFrameAnnotationCounts } from '../useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount';
import { useVideoAnnotationCounts } from '../useVideoAnnotationsCount/useVideoAnnotationsCount';
import { useImageAnnotationCounts } from '../useImageAnnotationCounts/useImageAnnotationCounts';
import {
    buildVideoAnnotationCountsFilter,
    buildVideoFrameAnnotationCountsFilter
} from '$lib/utils/buildAnnotationCountsFilters';
import { buildImageFilter } from '$lib/utils/buildImageFilter';
import { SampleType } from '$lib/api/lightly_studio_local/types.gen';
import type { useRouteType } from '../useRouteType/useRouteType';
import type { components } from '$lib/schema';
import type { Collection } from '$lib/services/types';
import type { Writable } from 'svelte/store';
import type { VideoFrameFieldsBoundsView } from '../useVideoFramesBounds/useVideoFramesBounds';
import type { VideoFieldsBoundsView } from '../useVideosBounds/useVideosBounds';
import type { DimensionBounds } from '../useDimensions/useDimensions';

type AnnotationsFilter = components['schemas']['AnnotationsFilter'];
type MetadataFilters = components['schemas']['MetadataFilters'];

interface AnnotationCountsAggregationParams {
    routeType: ReturnType<typeof useRouteType>;
    collectionId: string;
    datasetId: string;
    parentCollection: Collection | null;
    metadataFilters: MetadataFilters | undefined;
    annotationFilter: AnnotationsFilter | undefined;
    dimensionsValues: DimensionBounds | null;
    videoFramesBoundsValues: Writable<VideoFrameFieldsBoundsView | null>;
    videoBoundsValues: Writable<VideoFieldsBoundsView | null>;
    plotSelectionImageSampleIds: string[];
    plotSelectionVideoSampleIds: string[];
    onAnnotationCountsChange: (
        counts: { label_name: string; total_count: number; current_count?: number }[]
    ) => void;
}

/**
 * Hook to manage annotation counts based on the current route and filters.
 * Selects the appropriate annotation counts hook and aggregates total annotations.
 */
export function useAnnotationCountsAggregation({
    routeType,
    collectionId,
    datasetId,
    parentCollection,
    metadataFilters,
    annotationFilter,
    dimensionsValues,
    videoFramesBoundsValues,
    videoBoundsValues,
    plotSelectionImageSampleIds,
    plotSelectionVideoSampleIds,
    onAnnotationCountsChange
}: AnnotationCountsAggregationParams) {
    const videoFramesBoundsValue = get(videoFramesBoundsValues);
    const videoBoundsValue = get(videoBoundsValues);

    let annotationCounts;
    if (
        routeType.isVideoFrames ||
        (routeType.isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
    ) {
        let videoFrameCollectionId = collectionId;
        if (routeType.isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
            videoFrameCollectionId = parentCollection.collectionId;
        annotationCounts = useVideoFrameAnnotationCounts({
            collectionId: videoFrameCollectionId,
            filter: buildVideoFrameAnnotationCountsFilter({
                metadataFilters,
                annotationFilter,
                videoFramesBoundsValues: videoFramesBoundsValue ?? undefined
            })
        });
    } else if (routeType.isVideos) {
        annotationCounts = useVideoAnnotationCounts({
            collectionId,
            filter: buildVideoAnnotationCountsFilter({
                metadataFilters,
                annotationFilter,
                videoBoundsValues: videoBoundsValue ?? undefined,
                sampleIds: plotSelectionVideoSampleIds
            })
        });
    } else {
        annotationCounts = useImageAnnotationCounts({
            collectionId: datasetId,
            filter: buildImageFilter({
                dimensionsValues: dimensionsValues ?? undefined,
                annotationFilter,
                metadataFilters,
                sampleIds: routeType.isAnnotations ? [] : plotSelectionImageSampleIds
            })
        });
    }

    // Feed annotation counts back to the parent for UI-ready filter rows.
    // Only update when data is present to avoid flicker during query refetch.
    const unsubscribe = annotationCounts.subscribe((countsQuery) => {
        const countsData = countsQuery?.data;
        if (countsData) {
            onAnnotationCountsChange(
                countsData as { label_name: string; total_count: number; current_count?: number }[]
            );
        }
    });

    const totalAnnotations = derived(annotationCounts, ($annotationCounts) => {
        const countsData = $annotationCounts.data;
        if (!countsData) return 0;
        return countsData.reduce((sum, item) => sum + Number(item.total_count), 0);
    });

    // Cleanup subscription
    if (typeof window !== 'undefined') {
        const cleanup = () => unsubscribe();
        if (typeof window.addEventListener !== 'undefined') {
            window.addEventListener('beforeunload', cleanup);
        }
    }

    return {
        totalAnnotations
    };
}
