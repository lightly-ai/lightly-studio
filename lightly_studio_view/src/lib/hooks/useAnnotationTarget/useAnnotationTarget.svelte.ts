import { untrack } from 'svelte';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { getTargetBlockedReason, resolveTargetSource } from './resolveTargetSource';

/**
 * The annotation source new annotations are written to, and the action that changes it.
 * Keeps `annotationSourceBlockedReason` in the shared context up to date, so drawing tools refuse
 * to create an annotation while no source is picked or the picked one is hidden. Call it from
 * one always-mounted component of the sample details page.
 */
export const useAnnotationTarget = ({
    getCollectionId,
    getIsTargetHidden
}: {
    getCollectionId: () => string;
    getIsTargetHidden: () => boolean;
}) => {
    const { context, setAnnotationSource } = useAnnotationLabelContext();
    const { updateLastAnnotationSource, lastAnnotationSource } = useGlobalStorage();
    const annotationCollections = useAnnotationCollections(() => ({
        collectionId: getCollectionId()
    }));

    const sourceNames = $derived(annotationCollections.data?.map((c) => c.name) ?? []);
    const targetSource = $derived(resolveTargetSource(context.annotationSource, sourceNames));

    $effect(() => {
        context.annotationSourceBlockedReason = getTargetBlockedReason(
            targetSource,
            getIsTargetHidden()
        );
    });

    // Seed the context with the only source once the list has loaded.
    $effect(() => {
        if (!context.annotationSource && sourceNames.length === 1) {
            setAnnotationSource(sourceNames[0]);
        }
    });

    // Settings can rename the target source while this page is open. The rename updates the
    // stored source, so follow it.
    $effect(() =>
        lastAnnotationSource.subscribe((stored) => {
            const name = stored[untrack(getCollectionId)];
            if (name && name !== untrack(() => context.annotationSource)) {
                setAnnotationSource(name);
            }
        })
    );

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
