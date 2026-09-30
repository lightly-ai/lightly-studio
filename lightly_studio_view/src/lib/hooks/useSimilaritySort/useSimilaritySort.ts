import { derived, readonly, writable } from 'svelte/store';
import { SortDirection, type SimilaritySortExpr } from '$lib/api/lightly_studio_local';

const direction = writable<SortDirection>(SortDirection.DESC);
let currentSearch: unknown = undefined;

// `source` is required so the expression fits the discriminated `sort_by` unions.
const similaritySortBy = derived(
    direction,
    ($direction): SimilaritySortExpr & { source: 'similarity' } => ({
        source: 'similarity',
        direction: $direction
    })
);

/** Direction of the similarity sort while a text search is active. */
export const useSimilaritySort = () => {
    const toggleDirection = () => {
        direction.update((current) =>
            current === SortDirection.DESC ? SortDirection.ASC : SortDirection.DESC
        );
    };

    /** Resets to descending when the search changes. Searches are compared by identity. */
    const resetOnNewSearch = (search: unknown) => {
        if (search === currentSearch) {
            return;
        }
        currentSearch = search;
        direction.set(SortDirection.DESC);
    };

    return {
        direction: readonly(direction),
        similaritySortBy,
        toggleDirection,
        resetOnNewSearch
    };
};
