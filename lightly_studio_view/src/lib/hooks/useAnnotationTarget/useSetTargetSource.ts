import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

/**
 * Returns the action that picks where new annotations go and remembers the pick for the
 * collection. A hidden source is refused. Pass `isNew` for a name the user typed: it may name a
 * source that does not exist yet, which is created with the first annotation. Call it during
 * component init: it reads the annotation label context.
 */
export const useSetTargetSource = (
    getCollectionId: () => string
): ((name: string, options?: { isNew?: boolean }) => void) => {
    const { context } = useAnnotationLabelContext();
    const { updateLastAnnotationSource } = useGlobalStorage();

    return (name, options) => {
        const trimmed = name.trim();
        if (!trimmed || context.hiddenAnnotationSources?.includes(trimmed)) return;
        const collectionId = getCollectionId();
        if (options?.isNew) context.typedAnnotationSource = { collectionId, name: trimmed };
        updateLastAnnotationSource(collectionId, trimmed);
    };
};
