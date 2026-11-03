const storageKey = (collectionId: string) => `lightly-studio.pill-annotate-source.${collectionId}`;

/** The annotation source last picked in the Annotate popover of this collection, if any. */
export function readRememberedSource(collectionId: string): string | null {
    try {
        return localStorage.getItem(storageKey(collectionId));
    } catch {
        return null;
    }
}

export function rememberSource(collectionId: string, sourceName: string): void {
    try {
        localStorage.setItem(storageKey(collectionId), sourceName);
    } catch {
        // Storage can be full or blocked; the popover then asks again next time.
    }
}

/**
 * The remembered source when it can still take annotations: it must exist and be visible.
 * A deleted or hidden source counts as nothing remembered, so the user picks again.
 */
export function usableRememberedSource(
    remembered: string | null,
    sourceNames: string[],
    isHidden: (name: string) => boolean
): string | null {
    if (!remembered || !sourceNames.includes(remembered) || isHidden(remembered)) return null;
    return remembered;
}
