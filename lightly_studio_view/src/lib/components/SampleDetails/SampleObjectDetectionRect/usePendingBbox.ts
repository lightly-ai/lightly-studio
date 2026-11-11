import { get, readonly, writable } from 'svelte/store';
import type { BoundingBox } from '$lib/types';

interface PendingBox {
    token: number;
    bbox: BoundingBox;
    /** The created annotation, null while the creation runs. */
    annotationId: string | null;
}

/**
 * Keeps just-drawn boxes on screen while their annotations are created and the sample is
 * refetched. Without it a box disappears between the end of the drag and the refetched data.
 * With a sticky class the next box can be drawn before the last one is saved, so each box has
 * its own entry, addressed by the token that `start` returns.
 */
export function usePendingBbox() {
    const boxes = writable<PendingBox[]>([]);
    let newestToken = 0;

    // For removals only: the same length means nothing was removed, so subscribers stay quiet.
    const setBoxes = (next: PendingBox[]) => {
        if (next.length !== get(boxes).length) boxes.set(next);
    };

    /** Shows `drawn` until its annotation is in the sample data. Returns the token of the box. */
    const start = (drawn: BoundingBox): number => {
        const token = ++newestToken;
        boxes.update((list) => [...list, { token, bbox: { ...drawn }, annotationId: null }]);
        return token;
    };

    /** Records the annotation created for the box, so `sync` knows what to wait for. */
    const created = (token: number, annotationId: string) => {
        boxes.update((list) =>
            list.map((box) => (box.token === token ? { ...box, annotationId } : box))
        );
    };

    /** Hides the boxes whose created annotation is in `annotationIds`. */
    const sync = (annotationIds: string[]) => {
        const ids = new Set(annotationIds);
        setBoxes(get(boxes).filter((box) => !box.annotationId || !ids.has(box.annotationId)));
    };

    /** Hides the box, for example when its creation fails. */
    const clear = (token: number) => setBoxes(get(boxes).filter((box) => box.token !== token));

    /** Hides every box, for example when the view moves to another sample. A box started before
     *  is no longer the newest, so its creation does not select it on the next sample. */
    const clearAll = () => {
        newestToken++;
        setBoxes([]);
    };

    /** Whether no box was started after this one. */
    const isNewest = (token: number) => token === newestToken;

    return { boxes: readonly(boxes), start, created, sync, clear, clearAll, isNewest };
}
