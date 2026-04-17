import { writable, get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { useEmbedText } from '../useEmbedText/useEmbedText';
import type { TextEmbedding } from '$lib/types';
import type { Writable } from 'svelte/store';

/**
 * Hook to manage text-based embedding search.
 * Handles text query input, submission, and synchronization with global storage.
 */
export function useTextEmbeddingSearch({
    collectionId,
    textEmbedding,
    setTextEmbedding,
    activeImage
}: {
    collectionId: string;
    textEmbedding: Writable<TextEmbedding | undefined>;
    setTextEmbedding: (_textEmbedding: TextEmbedding | undefined) => void;
    activeImage: string | null;
}) {
    const query_textStore = writable(get(textEmbedding)?.queryText ?? '');
    const submittedQueryTextStore = writable(get(textEmbedding)?.queryText ?? '');
    let lastAppliedTextEmbeddingQuery = get(textEmbedding)?.queryText ?? '';

    // Create the embed text query - it will be reactive to changes in parameters
    const embedTextQuery = useEmbedText({
        collectionId,
        queryText: get(submittedQueryTextStore),
        embeddingModelId: null
    });

    const setError = (errorMessage: string) => {
        toast.error('Error', { description: errorMessage });
    };

    function handleKeyDown(event: KeyboardEvent) {
        const input = event.currentTarget as HTMLInputElement | null;

        if (event.key === 'Enter') {
            event.preventDefault();
            const trimmedQuery = get(query_textStore).trim();
            if (!trimmedQuery) {
                clearSearch();
                input?.blur();
                return;
            }

            query_textStore.set(trimmedQuery);
            submittedQueryTextStore.set(trimmedQuery);
            input?.blur();
        }

        if (event.key === 'Escape') {
            event.preventDefault();
            const submitted = get(submittedQueryTextStore);
            if (submitted) {
                query_textStore.set(submitted);
            } else {
                query_textStore.set('');
            }
            input?.blur();
        }
    }

    function clearSearch() {
        query_textStore.set('');
        submittedQueryTextStore.set('');
        setTextEmbedding(undefined);
    }

    // Sync with global storage when textEmbedding changes
    const unsubscribe1 = textEmbedding.subscribe(($textEmbedding) => {
        const committedQuery = $textEmbedding?.queryText ?? '';
        if (committedQuery === lastAppliedTextEmbeddingQuery) {
            return;
        }

        lastAppliedTextEmbeddingQuery = committedQuery;

        if (activeImage) {
            return;
        }

        if (!committedQuery) {
            submittedQueryTextStore.set('');
            query_textStore.set('');
            return;
        }

        submittedQueryTextStore.set(committedQuery);
        query_textStore.set(committedQuery);
    });

    // Handle embedding query results and errors - subscribe directly to query
    const unsubscribe2 = embedTextQuery.subscribe((queryResult) => {
        if (activeImage) return;

        if (queryResult.isError && queryResult.error) {
            const queryError = queryResult.error as
                | { error?: unknown; message?: string }
                | Error;
            const message = 'error' in queryError ? queryError.error : queryError.message;
            setError(String(message));
            return;
        }

        const submittedQueryText = get(submittedQueryTextStore);
        if (!submittedQueryText) {
            setTextEmbedding(undefined);
            return;
        }

        if (queryResult.isSuccess) {
            setTextEmbedding({
                queryText: submittedQueryText,
                embedding: queryResult.data
            });
        }
    });

    // Cleanup subscriptions
    if (typeof window !== 'undefined') {
        const cleanup = () => {
            unsubscribe1();
            unsubscribe2();
        };
        if (typeof window.addEventListener !== 'undefined') {
            window.addEventListener('beforeunload', cleanup);
        }
    }

    return {
        query_text: query_textStore,
        submittedQueryText: submittedQueryTextStore,
        handleKeyDown,
        clearSearch
    };
}
