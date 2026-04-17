import { derived, writable } from 'svelte/store';

const activeQueryTextByCollection = writable<Record<string, string>>({});

export function useQueryLanguage(collectionId: string) {
    const activeQueryText = derived(activeQueryTextByCollection, ($activeQueryTextByCollection) => {
        return $activeQueryTextByCollection[collectionId] ?? '';
    });

    const setQueryText = (text: string) => {
        activeQueryTextByCollection.update((state) => ({
            ...state,
            [collectionId]: text
        }));
    };

    const clearQueryText = () => {
        activeQueryTextByCollection.update((state) => ({
            ...state,
            [collectionId]: ''
        }));
    };

    return { activeQueryText, setQueryText, clearQueryText };
}
