import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

/**
 * Returns the action that sets where new annotations go and remembers it for the collection.
 * Call it during component init: it reads the annotation label context.
 */
export const useSetTargetSource = (getCollectionId: () => string): ((name: string) => void) => {
    const { setAnnotationSource } = useAnnotationLabelContext();
    const { updateLastAnnotationSource } = useGlobalStorage();

    return (name) => {
        const trimmed = name.trim();
        if (!trimmed) return;
        setAnnotationSource(trimmed);
        updateLastAnnotationSource(getCollectionId(), trimmed);
    };
};
