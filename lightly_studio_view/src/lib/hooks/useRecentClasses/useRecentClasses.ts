import { readonly, type Readable } from 'svelte/store';
import { useLocalStorage } from '$lib/hooks/useLocalStorage/useLocalStorage';
import { pushRecent } from './pushRecent';

const recentClasses = useLocalStorage<Record<string, string[]>>(
    'lightlyStudio_recent_annotation_classes',
    {}
);

/** Recently used classes per collection, newest first. */
export function useRecentClasses(): {
    recentClasses: Readable<Record<string, string[]>>;
    addRecentClass: (collectionId: string, className: string) => void;
    /** Follows a class rename in Settings. Keeps the position and drops a duplicate. */
    renameRecentClass: (collectionId: string, oldName: string, newName: string) => void;
    /** Forgets a class deleted in Settings. */
    removeRecentClass: (collectionId: string, className: string) => void;
} {
    const updateList = (collectionId: string, change: (list: string[]) => string[]) => {
        recentClasses.update((value) =>
            value[collectionId] ? { ...value, [collectionId]: change(value[collectionId]) } : value
        );
    };
    return {
        recentClasses: readonly(recentClasses),
        addRecentClass: (collectionId, className) => {
            recentClasses.update((value) => ({
                ...value,
                [collectionId]: pushRecent(value[collectionId] ?? [], className)
            }));
        },
        renameRecentClass: (collectionId, oldName, newName) => {
            updateList(collectionId, (list) => [
                ...new Set(list.map((name) => (name === oldName ? newName : name)))
            ]);
        },
        removeRecentClass: (collectionId, className) => {
            updateList(collectionId, (list) => list.filter((name) => name !== className));
        }
    };
}
