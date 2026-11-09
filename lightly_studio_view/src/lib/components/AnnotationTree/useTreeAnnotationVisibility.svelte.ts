import { fromStore } from 'svelte/store';
import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
import {
    toIsAnnotationVisible,
    useIsPairVisible
} from '$lib/hooks/useAnnotationTreeState/useIsPairVisible';

/**
 * The tree eyes as a check per annotation. `current` is undefined while the tree is off, so
 * callers keep their own visibility rules. `ready` says whether the class ids are loaded.
 */
export const useTreeAnnotationVisibility = (
    getParams: () => { collectionId: string; enabled: boolean }
) => {
    const labels = useAnnotationLabels(getParams);
    const isPairVisible = $derived(fromStore(useIsPairVisible(getParams().collectionId)));
    const current = $derived(
        getParams().enabled
            ? toIsAnnotationVisible(isPairVisible.current, labels.data ?? [])
            : undefined
    );

    return {
        get current() {
            return current;
        },
        get ready() {
            return !getParams().enabled || Boolean(labels.data);
        }
    };
};
