import type { Readable } from 'svelte/store';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useGlobalStorage } from '../useGlobalStorage';
import { useRecentClasses } from '../useRecentClasses/useRecentClasses';

/** Call during component init: it reads the annotation label context. */
export function useStickyClass(): {
    /** The class for the next annotation, per collection: the `lastAnnotationLabel` store. */
    stickyClasses: Readable<Record<string, string>>;
    /** An explicit class pick: sets the sticky class, puts it first in the recent list and
     *  sets the context label, so the crosshair color follows. */
    pickClass: (collectionId: string, className: string) => void;
} {
    const { lastAnnotationLabel, updateLastAnnotationLabel } = useGlobalStorage();
    const { addRecentClass } = useRecentClasses();
    const { setAnnotationLabel } = useAnnotationLabelContext();

    return {
        stickyClasses: lastAnnotationLabel,
        pickClass: (collectionId, className) => {
            updateLastAnnotationLabel(collectionId, className);
            addRecentClass(collectionId, className);
            setAnnotationLabel(className);
        }
    };
}
