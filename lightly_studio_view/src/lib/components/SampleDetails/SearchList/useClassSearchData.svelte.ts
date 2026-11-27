import { fromStore } from 'svelte/store';
import { useAnnotationLabels, useRecentClasses } from '$lib/hooks';

/**
 * The class names and the recent classes of a collection, for `ClassSearchList`. Call during
 * component init.
 */
export const useClassSearchData = (getCollectionId: () => string) => {
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const recentClasses = fromStore(useRecentClasses().recentClasses);

    // Stable arrays: the search list resets its first-row highlight when these change identity.
    const classNames = $derived((labels.data ?? []).map((label) => label.annotation_label_name));
    const recent = $derived(recentClasses.current[getCollectionId()] ?? []);

    return {
        get classNames() {
            return classNames;
        },
        get recent() {
            return recent;
        }
    };
};
