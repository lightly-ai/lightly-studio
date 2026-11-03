import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { resolveTargetSource } from './resolveTargetSource';

/**
 * The annotation source new annotations are written to, and the action that changes it.
 * Keeps `annotationSourceMissing` in the shared context up to date, so drawing tools refuse
 * to create an annotation while no source is picked. Call it from one always-mounted
 * component of the sample details page.
 */
export const useAnnotationTarget = (getCollectionId: () => string) => {
    const { context, setAnnotationSource } = useAnnotationLabelContext();
    const { updateLastAnnotationSource } = useGlobalStorage();
    const annotationCollections = useAnnotationCollections(() => ({
        collectionId: getCollectionId()
    }));

    const sourceNames = $derived(annotationCollections.data?.map((c) => c.name) ?? []);
    const targetSource = $derived(resolveTargetSource(context.annotationSource, sourceNames));

    $effect(() => {
        context.annotationSourceMissing = targetSource === null;
    });

    // Seed the context with the only source once the list has loaded.
    $effect(() => {
        if (!context.annotationSource && sourceNames.length === 1) {
            setAnnotationSource(sourceNames[0]);
        }
    });

    const setTargetSource = (name: string) => {
        const trimmed = name.trim();
        if (!trimmed) return;
        setAnnotationSource(trimmed);
        updateLastAnnotationSource(getCollectionId(), trimmed);
    };

    return {
        get targetSource() {
            return targetSource;
        },
        setTargetSource
    };
};
