import { readonly, writable } from 'svelte/store';

// Undefined keeps every annotation; true or false keeps those with or without an embedding.
const hasEmbedding = writable<boolean | undefined>(undefined);

/**
 * The "Has embedding" filter of the annotations grid and plot, shared across components.
 */
export function useAnnotationHasEmbeddingFilter() {
    return {
        hasEmbedding: readonly(hasEmbedding),
        setHasEmbedding: (value: boolean | undefined) => hasEmbedding.set(value)
    };
}
