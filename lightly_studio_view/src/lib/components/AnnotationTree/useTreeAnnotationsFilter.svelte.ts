import { fromStore } from 'svelte/store';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { buildTreeAnnotationsFilter } from '$lib/hooks/useAnnotationTreeState/buildTreeAnnotationsFilter';
import { useAnnotationTreeState } from '$lib/hooks/useAnnotationTreeState/useAnnotationTreeState';
import { createTreeActions } from './treeActions';
import { useAnnotationPairCounts } from './useAnnotationPairCounts.svelte';

/**
 * The annotation filter from the tree ticks of the collection, for the grid request.
 * `current` is undefined when nothing is unticked; `ready` says whether it is known yet.
 */
export const useTreeAnnotationsFilter = (
    getParams: () => { collectionId: string; filter?: ImageFilter | null; enabled: boolean }
) => {
    const sourcesQuery = useAnnotationCollections(() => {
        const { collectionId, enabled } = getParams();
        return { collectionId: enabled ? collectionId : undefined };
    });
    const pairsQuery = useAnnotationPairCounts(getParams);
    const treeState = $derived(useAnnotationTreeState(getParams().collectionId));
    const untickedPairs = $derived(fromStore(treeState.untickedPairs));
    const untickedUnannotated = $derived(fromStore(treeState.untickedUnannotated));

    const loaded = $derived(Boolean(pairsQuery.data && sourcesQuery.data));
    // A failed query lets the grid load without the tree filter, as if everything were ticked.
    const failed = $derived(pairsQuery.status === 'error' || sourcesQuery.status === 'error');
    const ready = $derived(!getParams().enabled || loaded || failed);
    const allPairs = $derived(
        (pairsQuery.data ?? []).map((count) => ({
            collection_id: count.annotation_collection_id,
            annotation_label_id: count.annotation_label_id
        }))
    );
    const sourceIds = $derived((sourcesQuery.data ?? []).map((source) => source.collection_id));

    const filter = $derived.by(() => {
        if (!getParams().enabled || !loaded) return undefined;
        return buildTreeAnnotationsFilter(
            allPairs,
            untickedPairs.current,
            untickedUnannotated.current,
            sourceIds
        );
    });

    const actions = createTreeActions(
        () => treeState,
        () => ({ allPairs, sourceIds })
    );

    return {
        get current() {
            return filter;
        },
        get ready() {
            return ready;
        },
        /** Does what "Only" on the class group does in "By class". */
        onlyClass: (className: string) => {
            const pairs = (pairsQuery.data ?? [])
                .filter((count) => count.label_name === className)
                .map((count) => ({
                    collection_id: count.annotation_collection_id,
                    annotation_label_id: count.annotation_label_id
                }));
            actions.onlyTargets(pairs, []);
        }
    };
};
