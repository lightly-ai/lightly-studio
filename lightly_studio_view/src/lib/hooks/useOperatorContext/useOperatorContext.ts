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
    isSamplesRoute,
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

export function resolveScopeLabel(sampleType: SampleType | null, isOnDetailPage: boolean): string {
    if (sampleType === null) return 'Full collection';
    return isOnDetailPage
        ? `Current ${sampleType.replaceAll('_', ' ')}`
        : `All ${sampleType.replaceAll('_', ' ')}s in the view`;
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
            ...(tagIds.length > 0 && { tag_ids: tagIds })
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

    const isOnDetailPage = derived(routeId, resolveIsDetailPage);
    const currentScope = derived(pageContext, ($p) => $p.sampleType as OperatorScope | null);
    const scopeLabel = derived(pageContext, ($p) =>
        resolveScopeLabel($p.sampleType, resolveIsDetailPage($p.routeId))
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
        currentScope,
        scopeLabel,
        isOnDetailPage,
        contextFilter
    };
}
