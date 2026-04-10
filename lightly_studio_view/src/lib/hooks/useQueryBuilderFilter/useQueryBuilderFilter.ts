import { writable, derived, type Readable } from 'svelte/store';
import { svarToQueryFilter } from '$lib/utils/svarToQueryFilter';
import type { IFilterSet } from '$lib/types/svar-filter';
import type { WireExpression } from '$lib/types/queryFilter';

// Module-level singleton so the layout panel and the samples page share state.
const filterSet = writable<IFilterSet | null>(null);

const queryFilter: Readable<WireExpression | undefined> = derived(filterSet, ($filterSet) =>
    svarToQueryFilter($filterSet)
);

export function useQueryBuilderFilter() {
    function updateFilterSet(set: IFilterSet | null) {
        filterSet.set(set);
    }

    function clearFilter() {
        filterSet.set(null);
    }

    return { filterSet, queryFilter, updateFilterSet, clearFilter };
}
