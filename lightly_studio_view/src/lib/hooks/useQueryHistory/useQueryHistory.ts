import { readonly, type Readable } from 'svelte/store';
import { useLocalStorage } from '$lib/hooks/useLocalStorage/useLocalStorage';
import { pushRecent } from '$lib/hooks/useRecentClasses/pushRecent';

const MAX_QUERIES_PER_COLLECTION = 10;

const queryHistory = useLocalStorage<Record<string, string[]>>('lightlyStudio_query_history', {});

interface UseQueryHistoryReturn {
    queryHistory: Readable<Record<string, string[]>>;
    addQuery: (collectionId: string, query: string) => void;
}

/** Applied queries per collection, newest first. */
export function useQueryHistory(): UseQueryHistoryReturn {
    return {
        queryHistory: readonly(queryHistory),
        addQuery: (collectionId, query) => {
            queryHistory.update((value) => ({
                ...value,
                [collectionId]: pushRecent(
                    value[collectionId] ?? [],
                    query,
                    MAX_QUERIES_PER_COLLECTION
                )
            }));
        }
    };
}
