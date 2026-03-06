import { derived, readable, type Readable } from 'svelte/store';
import type {
    AnnotationsFilter,
    SampleFilter,
    ImageFilter,
    VideoFrameFilter,
    VideoFilter,
    OperatorScope
} from '$lib/api/lightly_studio_local';
import { OperatorScope as OperatorScopeValues } from '$lib/api/lightly_studio_local';
import {
    isSampleDetailsRoute,
    isFrameDetailsRoute,
    isVideoDetailsRoute,
    isAnnotationDetailsRoute,
    isSamplesRoute,
    isVideosRoute,
    isVideoFramesRoute,
    isAnnotationsRoute,
    isCaptionsRoute,
    isGroupsRoute
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

export function resolveCurrentScope(routeId: string | null): OperatorScope | null {
    if (isSamplesRoute(routeId) || isSampleDetailsRoute(routeId)) return OperatorScopeValues.IMAGE;
    if (isVideosRoute(routeId) || isVideoDetailsRoute(routeId)) return OperatorScopeValues.VIDEO;
    if (isVideoFramesRoute(routeId) || isFrameDetailsRoute(routeId))
        return OperatorScopeValues.VIDEO_FRAME;
    if (isAnnotationsRoute(routeId) || isAnnotationDetailsRoute(routeId))
        return OperatorScopeValues.ANNOTATION;
    if (isGroupsRoute(routeId)) return OperatorScopeValues.GROUP;
    if (isCaptionsRoute(routeId)) return OperatorScopeValues.CAPTION;
    return null;
}

export function resolveScopeLabel(routeId: string | null): string {
    if (isSampleDetailsRoute(routeId)) return 'Current image';
    if (isFrameDetailsRoute(routeId)) return 'Current frame';
    if (isVideoDetailsRoute(routeId)) return 'Current video';
    if (isAnnotationDetailsRoute(routeId)) return 'Current annotation';
    if (isSamplesRoute(routeId)) return 'Current image collection';
    if (isVideosRoute(routeId)) return 'Current video collection';
    if (isVideoFramesRoute(routeId)) return 'Current frame collection';
    if (isAnnotationsRoute(routeId)) return 'Current annotation collection';
    if (isGroupsRoute(routeId)) return 'Current group collection';
    if (isCaptionsRoute(routeId)) return 'Current caption collection';
    return 'Full collection';
}

export function resolveContextFilter(
    { routeId, collectionId, sampleId, annotationId }: PageContext,
    imageFilter: ImageFilter | null,
    videoFilter: VideoFilter | null,
    frameFilter: VideoFrameFilter | null,
    annotationFilterIds: Set<string>,
    tagsSelected: Set<string>
): OperatorContextFilter {
    if (isAnnotationDetailsRoute(routeId) && annotationId) {
        return { collection_id: collectionId, sample_ids: [annotationId] } satisfies SampleFilter;
    }
    if (resolveIsDetailPage(routeId) && sampleId) {
        return { collection_id: collectionId, sample_ids: [sampleId] } satisfies SampleFilter;
    }
    if (isAnnotationsRoute(routeId)) {
        const labelIds = Array.from(annotationFilterIds);
        const tagIds = Array.from(tagsSelected);
        const filter: AnnotationsFilter = {
            ...(labelIds.length > 0 && { annotation_label_ids: labelIds }),
            ...(tagIds.length > 0 && { annotation_tag_ids: tagIds })
        };
        return Object.keys(filter).length > 0 ? filter : undefined;
    }
    if (isCaptionsRoute(routeId)) return { has_captions: true } satisfies SampleFilter;
    if (isSamplesRoute(routeId)) return imageFilter ?? undefined;
    if (isVideosRoute(routeId)) return videoFilter ?? undefined;
    if (isVideoFramesRoute(routeId)) return frameFilter ?? undefined;
    return undefined;
}

export function useOperatorContext(
    pageContext: Readable<PageContext>,
    tagsSelected: Readable<Set<string>> = readable(new Set<string>())
) {
    const routeId = derived(pageContext, ($p) => $p.routeId);
    const collectionId = derived(pageContext, ($p) => $p.collectionId);

    const isOnDetailPage = derived(routeId, resolveIsDetailPage);
    const currentScope = derived(routeId, resolveCurrentScope);
    const scopeLabel = derived(routeId, resolveScopeLabel);

    const isCollectionView = derived(
        routeId,
        ($r) => resolveCurrentScope($r) !== null && !resolveIsDetailPage($r)
    );

    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();
    const { frameFilter } = useFramesFilter();
    const { selectedAnnotationFilterIds } = useGlobalStorage();

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

    return {
        collectionId,
        currentScope,
        scopeLabel,
        isCollectionView,
        isOnDetailPage,
        contextFilter
    };
}
