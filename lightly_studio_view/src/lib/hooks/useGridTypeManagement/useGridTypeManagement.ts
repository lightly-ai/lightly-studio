import { derived, writable, type Readable } from 'svelte/store';
import type { GridType } from '$lib/types';
import type { useRouteType } from '../useRouteType/useRouteType';

/**
 * Hook to manage grid type based on current route.
 * Handles switching between different grid views and clearing selections when changing collections.
 */
export function useGridTypeManagement({
    collectionId,
    routeType,
    setLastGridType,
    clearSelectedSamples,
    clearSelectedSampleAnnotationCrops
}: {
    collectionId: string;
    routeType: ReturnType<typeof useRouteType>;
    setLastGridType: (gridType: GridType) => void;
    clearSelectedSamples: (collection_id: string) => void;
    clearSelectedSampleAnnotationCrops: (collectionId: string) => void;
}): { gridType: Readable<GridType> } {
    const gridTypeStore = writable<GridType>('samples');
    let lastCollectionId: string | null = null;

    // Derive gridType from routeType
    const unsubscribe = derived(
        [],
        () => {
            let nextGridType: GridType | null = null;

            if (routeType.isAnnotations) {
                nextGridType = 'annotations';
            } else if (routeType.isSamples) {
                nextGridType = 'samples';
            } else if (routeType.isCaptions) {
                nextGridType = 'captions';
            } else if (routeType.isVideoFrames) {
                nextGridType = 'video_frames';
            } else if (routeType.isVideos) {
                nextGridType = 'videos';
            } else if (routeType.isGroups) {
                nextGridType = 'groups';
            }

            if (!nextGridType) {
                return;
            }

            if (lastCollectionId && lastCollectionId !== collectionId) {
                clearSelectedSamples(lastCollectionId);
                clearSelectedSampleAnnotationCrops(lastCollectionId);
            }

            gridTypeStore.set(nextGridType);
            lastCollectionId = collectionId;

            // Temporary hack to remember where the user was when navigating
            // TODO: also remember state of tags, labels, metadata filters etc. Possible store it in pagestate
            setLastGridType(nextGridType);
        }
    ).subscribe(() => {});

    // Clean up subscription when component unmounts
    if (typeof window !== 'undefined') {
        const cleanup = () => unsubscribe();
        if (typeof window.addEventListener !== 'undefined') {
            window.addEventListener('beforeunload', cleanup);
        }
    }

    return {
        gridType: gridTypeStore
    };
}
