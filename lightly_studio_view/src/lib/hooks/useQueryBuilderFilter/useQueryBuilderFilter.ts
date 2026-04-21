import { writable } from 'svelte/store';

// Module-level singleton so the layout panel and the samples page share state.
const pythonQuery = writable<string | null>(null);

export function useQueryBuilderFilter() {
    function updatePythonQuery(query: string | null) {
        pythonQuery.set(query);
    }

    function clearFilter() {
        pythonQuery.set(null);
    }

    return { pythonQuery, updatePythonQuery, clearFilter };
}
