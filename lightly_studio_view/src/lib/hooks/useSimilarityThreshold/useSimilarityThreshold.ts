import { readonly, writable } from 'svelte/store';

/**
 * What the threshold belongs to. A change of any field starts a new scope and clears the
 * threshold. Fields are compared by identity, so each new search embedding is a new scope.
 */
interface SimilarityThresholdScope {
    search: unknown;
    collectionId: string;
    gridType: string;
}

const threshold = writable<number | null>(null);
let currentScope: SimilarityThresholdScope | null = null;

const isSameScope = (a: SimilarityThresholdScope | null, b: SimilarityThresholdScope) =>
    a !== null &&
    a.search === b.search &&
    a.collectionId === b.collectionId &&
    a.gridType === b.gridType;

export const useSimilarityThreshold = () => {
    const setThreshold = (value: number) => {
        threshold.set(value);
    };

    const clearThreshold = () => {
        threshold.set(null);
    };

    const resetOnScopeChange = (scope: SimilarityThresholdScope) => {
        if (isSameScope(currentScope, scope)) {
            return;
        }
        currentScope = { ...scope };
        clearThreshold();
    };

    return {
        threshold: readonly(threshold),
        setThreshold,
        clearThreshold,
        resetOnScopeChange
    };
};
