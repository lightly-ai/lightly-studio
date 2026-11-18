import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import type { CuboidAnnotation } from '../domain';
import {
    cuboidToVisibilityRef,
    getTrackVisibilityKey,
    isAnnotationHidden,
    tickAnnotationToVisibilityRef,
    toggleSetEntry
} from './annotationVisibility';

/**
 * The sources and tracks the user hid in the workspace. A hidden track stays hidden on every
 * tick. Everything shows again when the reset key changes.
 */
export function useAnnotationVisibility(getResetKey: () => string) {
    let hiddenSourceIds = $state.raw<ReadonlySet<string>>(new Set());
    let hiddenTrackKeys = $state.raw<ReadonlySet<string>>(new Set());
    const hidden = $derived({ sourceIds: hiddenSourceIds, trackKeys: hiddenTrackKeys });

    $effect(() => {
        getResetKey();
        hiddenSourceIds = new Set();
        hiddenTrackKeys = new Set();
    });

    return {
        isCuboidHidden: (cuboid: CuboidAnnotation) =>
            isAnnotationHidden(cuboidToVisibilityRef(cuboid), hidden),
        isTickAnnotationHidden: (annotation: TickDetailView['annotations'][number]) =>
            isAnnotationHidden(tickAnnotationToVisibilityRef(annotation), hidden),
        isSourceHidden: (sourceId: string) => hiddenSourceIds.has(sourceId),
        toggleTrack: (cuboid: CuboidAnnotation) => {
            hiddenTrackKeys = toggleSetEntry(
                hiddenTrackKeys,
                getTrackVisibilityKey(cuboidToVisibilityRef(cuboid))
            );
        },
        toggleSource: (sourceId: string) => {
            hiddenSourceIds = toggleSetEntry(hiddenSourceIds, sourceId);
        }
    };
}
