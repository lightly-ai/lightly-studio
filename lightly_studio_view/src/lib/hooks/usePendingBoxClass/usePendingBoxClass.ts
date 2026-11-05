import { readonly, writable, type Readable } from 'svelte/store';
import type { BoundingBox } from '$lib/types';

// Module level: the canvas asks for the class and the image container shows the card.
const request = writable<{ bbox: BoundingBox } | null>(null);
let settle: ((className: string | null) => void) | null = null;

const finish = (className: string | null) => {
    const current = settle;
    settle = null;
    request.set(null);
    current?.(className);
};

interface UsePendingBoxClassReturn {
    request: Readable<{ bbox: BoundingBox } | null>;
    /** Shows the pending-box card at `bbox`. Resolves with the picked class, or null.
     *  A new request resolves the previous one with null. */
    requestClass: (bbox: BoundingBox) => Promise<string | null>;
    /** No-op when nothing is pending. */
    resolve: (className: string) => void;
    /** No-op when nothing is pending. */
    cancel: () => void;
}

/** A drawn box that waits for a class picked at the box before it is saved. */
export function usePendingBoxClass(): UsePendingBoxClassReturn {
    return {
        request: readonly(request),
        requestClass: (bbox) => {
            finish(null);
            request.set({ bbox: { ...bbox } });
            return new Promise((resolve) => {
                settle = resolve;
            });
        },
        resolve: (className) => {
            if (settle) finish(className);
        },
        cancel: () => {
            if (settle) finish(null);
        }
    };
}
