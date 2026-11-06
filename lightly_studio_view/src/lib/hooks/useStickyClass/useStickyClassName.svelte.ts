import { fromStore } from 'svelte/store';
import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
import { resolveStickyClass, useStickyClass } from './useStickyClass';

/**
 * The class new annotations of the collection get, or undefined when none is set. A stored
 * class that was deleted elsewhere counts as unset, see `resolveStickyClass`.
 */
export const useStickyClassName = (getCollectionId: () => string) => {
    const stickyClasses = fromStore(useStickyClass().stickyClasses);
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const className = $derived(
        resolveStickyClass({
            collectionId: getCollectionId(),
            stickyClass: stickyClasses.current[getCollectionId()],
            classNames: labels.data?.map((label) => label.annotation_label_name ?? '')
        })
    );

    return {
        get current() {
            return className;
        }
    };
};
