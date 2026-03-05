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

export function useOperatorContext(
    pageContext: Readable<PageContext>,
    tagsSelected: Readable<Set<string>> = readable(new Set<string>())
) {
    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();
    const { frameFilter } = useFramesFilter();
    const { selectedAnnotationFilterIds } = useGlobalStorage();

    const collectionId = derived(pageContext, ($p) => $p.collectionId);
    const routeId = derived(pageContext, ($p) => $p.routeId);

    const isSampleDetail = derived(routeId, ($r) => isSampleDetailsRoute($r));
    const isFrameDetail = derived(routeId, ($r) => isFrameDetailsRoute($r));
    const isVideoDetail = derived(routeId, ($r) => isVideoDetailsRoute($r));
    const isAnnotationDetail = derived(routeId, ($r) => isAnnotationDetailsRoute($r));

    const isOnDetailPage = derived(
        [isSampleDetail, isFrameDetail, isVideoDetail, isAnnotationDetail],
        ([$s, $f, $v, $a]) => $s || $f || $v || $a
    );

    const currentScope = derived(routeId, ($r): OperatorScope | null => {
        if (isSamplesRoute($r) || isSampleDetailsRoute($r)) return OperatorScopeValues.IMAGE;
        if (isVideosRoute($r) || isVideoDetailsRoute($r)) return OperatorScopeValues.VIDEO;
        if (isVideoFramesRoute($r) || isFrameDetailsRoute($r))
            return OperatorScopeValues.VIDEO_FRAME;
        if (isAnnotationsRoute($r) || isAnnotationDetailsRoute($r))
            return OperatorScopeValues.ANNOTATION;
        if (isGroupsRoute($r)) return OperatorScopeValues.GROUP;
        if (isCaptionsRoute($r)) return OperatorScopeValues.CAPTION;
        return null;
    });

    const scopeLabel = derived(
        [routeId, isSampleDetail, isFrameDetail, isVideoDetail, isAnnotationDetail],
        ([$r, $isSample, $isFrame, $isVideo, $isAnnotation]) => {
            if ($isSample) return 'Current image';
            if ($isFrame) return 'Current frame';
            if ($isVideo) return 'Current video';
            if ($isAnnotation) return 'Current annotation';
            if (isSamplesRoute($r)) return 'Current image collection';
            if (isVideosRoute($r)) return 'Current video collection';
            if (isVideoFramesRoute($r)) return 'Current frame collection';
            if (isAnnotationsRoute($r)) return 'Current annotation collection';
            if (isGroupsRoute($r)) return 'Current group collection';
            if (isCaptionsRoute($r)) return 'Current caption collection';
            return 'Full collection';
        }
    );

    const isCollectionView = derived(
        [routeId, isOnDetailPage],
        ([$r, $isDetail]) =>
            !$isDetail &&
            (isSamplesRoute($r) ||
                isVideosRoute($r) ||
                isVideoFramesRoute($r) ||
                isAnnotationsRoute($r) ||
                isGroupsRoute($r) ||
                isCaptionsRoute($r))
    );

    const contextFilter = derived(
        [
            pageContext,
            imageFilter,
            videoFilter,
            frameFilter,
            selectedAnnotationFilterIds,
            tagsSelected,
            isOnDetailPage
        ],
        ([
            $p,
            $imageFilter,
            $videoFilter,
            $frameFilter,
            $annotationFilterIds,
            $tagsSelected,
            $isOnDetailPage
        ]): OperatorContextFilter => {
            const { routeId: $r, collectionId: $cid, sampleId: $sid, annotationId: $aid } = $p;

            const isAnnotationDetail = isAnnotationDetailsRoute($r);

            if (isAnnotationDetail && $aid) {
                return { collection_id: $cid, sample_ids: [$aid] } satisfies SampleFilter;
            }
            if ($isOnDetailPage && $sid) {
                return { collection_id: $cid, sample_ids: [$sid] } satisfies SampleFilter;
            }
            if (isAnnotationsRoute($r)) {
                const labelIds = Array.from($annotationFilterIds);
                const tagIds = Array.from($tagsSelected);
                const filter: AnnotationsFilter = {
                    ...(labelIds.length > 0 && { annotation_label_ids: labelIds }),
                    ...(tagIds.length > 0 && { annotation_tag_ids: tagIds })
                };
                return Object.keys(filter).length > 0 ? filter : undefined;
            }
            if (isCaptionsRoute($r)) {
                return { has_captions: true } satisfies SampleFilter;
            }
            if (isSamplesRoute($r)) return $imageFilter ?? undefined;
            if (isVideosRoute($r)) return $videoFilter ?? undefined;
            if (isVideoFramesRoute($r)) return $frameFilter ?? undefined;
            return undefined;
        }
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
