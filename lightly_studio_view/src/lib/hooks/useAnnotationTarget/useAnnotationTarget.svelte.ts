import { untrack } from 'svelte';
import { fromStore, get } from 'svelte/store';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { listHiddenSources } from './listHiddenSources';
import { isPickRemoved, resolveTargetSource } from './resolveTargetSource';

interface UseAnnotationTargetParams {
    getCollectionId: () => string;
    /** The annotations of the sample on screen. */
    getAnnotations: () => AnnotationView[];
    /** The annotations hidden in the Annotations panel. */
    getHiddenIds: () => Set<string>;
}

/**
 * Resolves the annotation source new annotations go to and writes it, with the reason new
 * annotations are blocked and the hidden sources, into the annotation label context. This is the
 * only writer of those fields. Drawing tools read them, and `useSetTargetSource` changes the
 * pick. Call it once, from the component that creates the context.
 */
export const useAnnotationTarget = (params: UseAnnotationTargetParams) => {
    const { getCollectionId } = params;
    const { context } = useAnnotationLabelContext();
    const picks = fromStore(useGlobalStorage().lastAnnotationSource);
    const sources = useAnnotationCollections(() => ({ collectionId: getCollectionId() }));

    const sourceNames = $derived(sources.data?.map((source) => source.name));
    const hiddenSources = $derived(
        listHiddenSources(sources.data ?? [], params.getAnnotations(), params.getHiddenIds())
    );
    const target = $derived(
        resolveTargetSource({
            pick: picks.current[getCollectionId()],
            typedSource: context.typedAnnotationSource,
            sourceNames,
            isError: sources.isError,
            hiddenSources
        })
    );

    $effect(() => {
        context.annotationSource = target.targetSource;
        context.annotationSourceBlockedReason = target.blockedReason;
        context.hiddenAnnotationSources = hiddenSources;
    });

    forgetRemovedPick(getCollectionId, () => sourceNames);
};

// Another tab or the Python API can rename or delete the picked source. Either way the pick is
// forgotten, so the next annotation asks for a source instead of re-creating the removed one or
// going to a source that only looks like a rename.
const forgetRemovedPick = (
    getCollectionId: () => string,
    getSourceNames: () => string[] | undefined
) => {
    const { lastAnnotationSource, removeLastAnnotationSource } = useGlobalStorage();
    // Not reactive on purpose: it must not re-trigger the effect.
    let previous: { collectionId: string; names: string[] } | undefined;
    $effect(() => {
        const names = getSourceNames();
        const collectionId = getCollectionId();
        if (!names) return;
        untrack(() => {
            if (previous?.collectionId !== collectionId) return;
            const pick = get(lastAnnotationSource)[collectionId];
            if (pick && isPickRemoved({ pick, previousNames: previous.names, nextNames: names })) {
                removeLastAnnotationSource(collectionId, pick);
            }
        });
        previous = { collectionId, names };
    });
};
