import { derived, readable, type Readable } from 'svelte/store';
import type {
    AnnotationsFilter,
    SampleFilter,
    ImageFilter,
    VideoFrameFilter,
    VideoFilter,
    OperatorContextRequest,
    OperatorScope,
    SampleType
} from '$lib/api/lightly_studio_local';
import {
    isSampleDetailsRoute,
    isFrameDetailsRoute,
    isVideoDetailsRoute,
    isAnnotationDetailsRoute,
    isImagesRoute,
    isVideosRoute,
    isVideoFramesRoute,
    isAnnotationsRoute,
    isCaptionsRoute
} from '$lib/routes';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { useFramesFilter } from '$lib/hooks/useFramesFilter/useFramesFilter';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import {
    buildSimilarityThresholdFilter,
    useSimilarityThreshold
} from '$lib/hooks/useSimilarityThreshold';

type SimilarityThresholdFilter = ReturnType<typeof buildSimilarityThresholdFilter>;

export type PageContext = {
    routeId: string | null;
    collectionId: string;
    sampleId: string | null;
    annotationId: string | null;
    sampleType: SampleType | null;
};

export type OperatorContextFilter = OperatorContextRequest['context_filter'];

export function resolveIsDetailPage(routeId: string | null): boolean {
    return (
        isSampleDetailsRoute(routeId) ||
        isFrameDetailsRoute(routeId) ||
        isVideoDetailsRoute(routeId) ||
        isAnnotationDetailsRoute(routeId)
    );
}

export function resolveScopeLabel(
    sampleType: SampleType | null,
    isOnDetailPage: boolean,
    scopeCount: number,
    hasActiveFilter: boolean
): string {
    if (sampleType === null) return 'the entire collection';
    if (isOnDetailPage) {
        return `the currently viewed ${sampleType.replaceAll('_', ' ')}`;
    }
    const typeName = sampleType.replaceAll('_', ' ');
    const plural = scopeCount === 1 ? typeName : `${typeName}s`;
    if (hasActiveFilter) {
        return `${scopeCount} filtered ${plural}`;
    }
    return `all ${scopeCount} ${plural}`;
}

export function resolveContextFilter(
    { routeId, sampleId, annotationId }: PageContext,
    imageFilter: ImageFilter | null,
    videoFilter: VideoFilter | null,
    frameFilter: VideoFrameFilter | null,
    annotationFilterIds: Set<string>,
    tagsSelected: Set<string>,
    annotationThresholdFilter: SimilarityThresholdFilter = {}
): OperatorContextFilter {
    if (isAnnotationDetailsRoute(routeId) && annotationId) {
        return { filter_type: 'sample', sample_ids: [annotationId] } satisfies SampleFilter;
    }
    if (resolveIsDetailPage(routeId) && sampleId) {
        return { filter_type: 'sample', sample_ids: [sampleId] } satisfies SampleFilter;
    }
    if (isAnnotationsRoute(routeId)) {
        const labelIds = Array.from(annotationFilterIds);
        const tagIds = Array.from(tagsSelected);
        const hasThreshold = annotationThresholdFilter.min_similarity !== undefined;
        if (labelIds.length === 0 && tagIds.length === 0 && !hasThreshold) return undefined;
        return {
            filter_type: 'annotations',
            ...(labelIds.length > 0 && { annotation_label_ids: labelIds }),
            ...(tagIds.length > 0 && { tag_ids: tagIds }),
            ...annotationThresholdFilter
        } satisfies AnnotationsFilter;
    }
    if (isCaptionsRoute(routeId))
        return { filter_type: 'sample', has_captions: true } satisfies SampleFilter;
    if (isImagesRoute(routeId))
        return imageFilter ? { ...imageFilter, filter_type: 'image' } : undefined;
    if (isVideosRoute(routeId))
        return videoFilter ? { ...videoFilter, filter_type: 'video' } : undefined;
    if (isVideoFramesRoute(routeId))
        return frameFilter ? { ...frameFilter, filter_type: 'video_frame' } : undefined;
    return undefined;
}

export function useOperatorContext(
    pageContext: Readable<PageContext>,
    tagsSelected: Readable<Set<string>> = readable(new Set<string>())
) {
    const routeId = derived(pageContext, ($p) => $p.routeId);

    const isOnDetailPage = derived(routeId, resolveIsDetailPage);
    const currentScope = derived(pageContext, ($p) => $p.sampleType as OperatorScope | null);

    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();
    const { frameFilter } = useFramesFilter();
    const {
        selectedAnnotationFilterIds,
        filteredSampleCount,
        filteredAnnotationCount,
        textEmbedding
    } = useGlobalStorage();
    const { threshold: similarityThreshold } = useSimilarityThreshold();
    const annotationThresholdFilter = derived(
        [textEmbedding, similarityThreshold],
        ([$textEmbedding, $threshold]) =>
            buildSimilarityThresholdFilter($textEmbedding?.embedding, $threshold)
    );

    const contextFilter = derived(
        [
            pageContext,
            imageFilter,
            videoFilter,
            frameFilter,
            selectedAnnotationFilterIds,
            tagsSelected,
            annotationThresholdFilter
        ],
        ([
            $p,
            $imageFilter,
            $videoFilter,
            $frameFilter,
            $annotationFilterIds,
            $tagsSelected,
            $annotationThresholdFilter
        ]): OperatorContextFilter =>
            resolveContextFilter(
                $p,
                $imageFilter,
                $videoFilter,
                $frameFilter,
                $annotationFilterIds,
                $tagsSelected,
                $annotationThresholdFilter
            )
    );

    // True only when the user has applied explicit filters — excludes intrinsic route constraints
    // (e.g. the captions route always sends has_captions:true, which is not a user-applied filter).
    const hasActiveFilter = derived(
        [
            routeId,
            imageFilter,
            videoFilter,
            frameFilter,
            selectedAnnotationFilterIds,
            tagsSelected,
            annotationThresholdFilter
        ],
        ([
            $routeId,
            $imageFilter,
            $videoFilter,
            $frameFilter,
            $annotationFilterIds,
            $tagsSelected,
            $annotationThresholdFilter
        ]) => {
            if (isAnnotationsRoute($routeId)) {
                return (
                    $annotationFilterIds.size > 0 ||
                    $tagsSelected.size > 0 ||
                    $annotationThresholdFilter.min_similarity !== undefined
                );
            }
            if (isImagesRoute($routeId)) return $imageFilter !== null;
            if (isVideosRoute($routeId)) return $videoFilter !== null;
            if (isVideoFramesRoute($routeId)) return $frameFilter !== null;
            return false;
        }
    );

    const scopeCount = derived(
        [routeId, filteredSampleCount, filteredAnnotationCount],
        ([$routeId, $sampleCount, $annotationCount]) =>
            isAnnotationsRoute($routeId) ? $annotationCount : $sampleCount
    );

    const scopeLabel = derived(
        [pageContext, isOnDetailPage, scopeCount, hasActiveFilter],
        ([$p, $isDetail, $count, $hasFilter]) =>
            resolveScopeLabel($p.sampleType, $isDetail, $count, $hasFilter)
    );

    return {
        currentScope,
        scopeLabel,
        isOnDetailPage,
        contextFilter
    };
}
