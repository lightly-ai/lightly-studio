import { derived, type Readable } from 'svelte/store';
import { pushRecent } from '$lib/components/SampleDetails/AnnotationCard/annotationCard.helpers';
import { useWebStorage } from '../useWebStorage/useWebStorage';

const recentClasses = useWebStorage<Record<string, string[]>>(
    'localStorage',
    'lightlyStudio_recent_annotation_classes',
    {}
);

/** Recently used classes per collection, newest first. */
export function useRecentClasses(): {
    recentClasses: Readable<Record<string, string[]>>;
    addRecentClass: (collectionId: string, className: string) => void;
} {
    return {
        recentClasses: derived(recentClasses, (value) => value),
        addRecentClass: (collectionId, className) => {
            recentClasses.update((value) => ({
                ...value,
                [collectionId]: pushRecent(value[collectionId] ?? [], className)
            }));
        }
    };
}
