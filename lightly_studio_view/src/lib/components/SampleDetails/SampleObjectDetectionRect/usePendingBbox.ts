import { get, writable } from 'svelte/store';
import type { BoundingBox } from '$lib/types';

/**
 * Keeps a just-drawn box on screen while the annotation is created and the sample is refetched.
 * Without it the box disappears between the end of the drag and the refetched data.
 */
export function usePendingBbox() {
    const bbox = writable<BoundingBox | null>(null);
    let createdAnnotationId: string | null = null;

    /** Shows `drawn` until the created annotation is in the sample data. */
    const start = (drawn: BoundingBox) => {
        createdAnnotationId = null;
        bbox.set({ ...drawn });
    };

    /** Records the id of the created annotation, so `sync` knows what to wait for. */
    const created = (annotationId: string) => {
        createdAnnotationId = annotationId;
    };

    /** Hides the box once the created annotation is in `annotationIds`. */
    const sync = (annotationIds: string[]) => {
        if (get(bbox) && createdAnnotationId && annotationIds.includes(createdAnnotationId)) {
            clear();
        }
    };

    const clear = () => {
        createdAnnotationId = null;
        bbox.set(null);
    };

    return { bbox, start, created, sync, clear };
}
