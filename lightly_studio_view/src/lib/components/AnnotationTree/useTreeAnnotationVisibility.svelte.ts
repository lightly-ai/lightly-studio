import { fromStore } from 'svelte/store';
import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
import { treeStateKey } from '$lib/hooks/useAnnotationTreeState/useAnnotationTreeState';
import {
    toIsAnnotationVisible,
    useIsPairVisible
} from '$lib/hooks/useAnnotationTreeState/useIsPairVisible';

/**
 * The tree eyes as a check per annotation. `current` is undefined while the tree is off, so
 * callers keep their own visibility rules. `ready` says whether the class ids are loaded.
 * With a `sourceId`, as on the Annotations grid, the eyes are those of that tab.
 */
export const useTreeAnnotationVisibility = (
    getParams: () => { collectionId: string; enabled?: boolean; sourceId?: string }
) => {
    const isEnabled = () => getParams().enabled ?? true;
    const labels = useAnnotationLabels(getParams);
    const isPairVisible = $derived(
        fromStore(useIsPairVisible(treeStateKey(getParams().collectionId, getParams().sourceId)))
    );
    const current = $derived(
        isEnabled() ? toIsAnnotationVisible(isPairVisible.current, labels.data ?? []) : undefined
    );

    return {
        get current() {
            return current;
        },
        get ready() {
            return !isEnabled() || Boolean(labels.data);
        }
    };
};
