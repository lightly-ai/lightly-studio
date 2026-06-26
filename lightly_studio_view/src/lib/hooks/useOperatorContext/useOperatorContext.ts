import { derived, readable, type Readable } from 'svelte/store';
import type {
    AnnotationsFilter,
    SampleFilter,
    ImageFilter,
    VideoFrameFilter,
    VideoFilter,
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

export type PageContext = {
    routeId: string | null;
    collectionId: string;
    sampleId: string | null;
    annotationId: string | null;
    sampleType: SampleType | null;
};

export type OperatorContextFilter =
    | ImageFilter
    | VideoFrameFilter
    | VideoFilter
    | AnnotationsFilter
    | SampleFilter
    | undefined;

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
    if (hasActiveFilter) {
        return `${scopeCount} filtered ${typeName}s`;
    }
    return `all ${scopeCount} ${typeName}s`;
}

export function resolveContextFilter(
    { routeId, sampleId, annotationId }: PageContext,
    imageFilter: ImageFilter | null,
    videoFilter: VideoFilter | null,
    frameFilter: VideoFrameFilter | null,
    annotationFilterIds: Set<string>,
    tagsSelected: Set<string>
): OperatorContextFilter {
    if (isAnnotationDetailsRoute(routeId) && annotationId) {
        return { sample_ids: [annotationId] } satisfies SampleFilter;
    }
    if (resolveIsDetailPage(routeId) && sampleId) {
        return { sample_ids: [sampleId] } satisfies SampleFilter;
    }
    if (isAnnotationsRoute(routeId)) {
        const labelIds = Array.from(annotationFilterIds);
        const tagIds = Array.from(tagsSelected);
        const filter: AnnotationsFilter = {
            ...(labelIds.length > 0 && { annotation_label_ids: labelIds }),
            ...(tagIds.length > 0 && { tag_ids: tagIds })
        };
        return Object.keys(filter).length > 0 ? filter : undefined;
    }
    if (isCaptionsRoute(routeId)) return { has_captions: true } satisfies SampleFilter;
    if (isImagesRoute(routeId)) return imageFilter ?? undefined;
    if (isVideosRoute(routeId)) return videoFilter ?? undefined;
    if (isVideoFramesRoute(routeId)) return frameFilter ?? undefined;
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
    const { selectedAnnotationFilterIds, filteredSampleCount, filteredAnnotationCount } =
        useGlobalStorage();

    const contextFilter = derived(
        [
            pageContext,
            imageFilter,
            videoFilter,
            frameFilter,
            selectedAnnotationFilterIds,
            tagsSelected
        ],
        ([
            $p,
            $imageFilter,
            $videoFilter,
            $frameFilter,
            $annotationFilterIds,
            $tagsSelected
        ]): OperatorContextFilter =>
            resolveContextFilter(
                $p,
                $imageFilter,
                $videoFilter,
                $frameFilter,
                $annotationFilterIds,
                $tagsSelected
            )
    );

    // True only when the user has applied explicit filters — excludes intrinsic route constraints
    // (e.g. the captions route always sends has_captions:true, which is not a user-applied filter).
    const hasActiveFilter = derived(
        [routeId, imageFilter, videoFilter, frameFilter, selectedAnnotationFilterIds, tagsSelected],
        ([
            $routeId,
            $imageFilter,
            $videoFilter,
            $frameFilter,
            $annotationFilterIds,
            $tagsSelected
        ]) => {
            if (isAnnotationsRoute($routeId)) {
                return $annotationFilterIds.size > 0 || $tagsSelected.size > 0;
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
