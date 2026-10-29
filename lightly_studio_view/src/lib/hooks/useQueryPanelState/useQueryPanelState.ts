import { writable, type Writable } from 'svelte/store';
import type { QueryExpression } from '$lib/hooks/useImageFilters/useImageFilters';

interface QueryPanelState {
    /** Text in the query editor, applied or not. Null until the user edits it. */
    draft: Writable<string | null>;
    /** Last applied query. The query filter chip keeps it while the filter is off. */
    lastQueryExpression: Writable<QueryExpression | null>;
}

// In memory only, so the state lasts for the session.
const stateByCollection = new Map<string, QueryPanelState>();

/**
 * Keeps the query panel state of a collection outside the components that show it, so it
 * survives closing the query editor, switching side panels, opening a sample and switching tabs.
 */
export function useQueryPanelState(collectionId: string): QueryPanelState {
    let state = stateByCollection.get(collectionId);
    if (!state) {
        state = { draft: writable(null), lastQueryExpression: writable(null) };
        stateByCollection.set(collectionId, state);
    }
    return state;
}
