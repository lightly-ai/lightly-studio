import type { Readable } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useRecentClasses } from '$lib/hooks/useRecentClasses/useRecentClasses';

// Classes picked since the page loaded, per collection. Such a class may not be in the class
// list yet: a new class is created with its first annotation.
const pickedClasses = new Set<string>();
const pickKey = (collectionId: string, className: string) => `${collectionId}/${className}`;

/**
 * The sticky class of a collection, if new annotations may use it. A class restored from an
 * earlier visit that is no longer in `classNames` was deleted elsewhere, so it counts as unset
 * instead of being re-created. While `classNames` loads, the stored class is used.
 */
export const resolveStickyClass = ({
    collectionId,
    stickyClass,
    classNames
}: {
    collectionId: string;
    stickyClass: string | undefined;
    classNames: string[] | undefined;
}): string | undefined => {
    if (!stickyClass || !classNames || classNames.includes(stickyClass)) return stickyClass;
    return pickedClasses.has(pickKey(collectionId, stickyClass)) ? stickyClass : undefined;
};

export function useStickyClass(): {
    /** The stored class for the next annotation, per collection: the `lastAnnotationLabel`
     *  store. Check it with `resolveStickyClass` or read `useStickyClassName` before use. */
    stickyClasses: Readable<Record<string, string>>;
    /** An explicit class pick: sets the sticky class and puts it first in the recent list. */
    pickClass: (collectionId: string, className: string) => void;
} {
    const { lastAnnotationLabel, updateLastAnnotationLabel } = useGlobalStorage();
    const { addRecentClass } = useRecentClasses();

    return {
        stickyClasses: lastAnnotationLabel,
        pickClass: (collectionId, className) => {
            pickedClasses.add(pickKey(collectionId, className));
            updateLastAnnotationLabel(collectionId, className);
            addRecentClass(collectionId, className);
        }
    };
}
