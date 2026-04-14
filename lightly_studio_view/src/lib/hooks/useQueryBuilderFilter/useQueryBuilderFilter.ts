import { writable, derived, type Readable } from 'svelte/store';
import { svarToQueryFilter } from '$lib/utils/svarToQueryFilter';
import type { IFilterSet } from '$lib/types/svar-filter';
import type { components } from '$lib/schema';
type QueryFieldSchema = components['schemas']['QueryFieldSchema'];
type WireExpression = components['schemas']['WireField'] | components['schemas']['WireTagsContains'] | components['schemas']['WireAnd'] | components['schemas']['WireOr'] | components['schemas']['WireNot'];

// Module-level singletons so the layout panel and the samples page share state.
const filterSet = writable<IFilterSet | null>(null);
const fieldSchemas = writable<QueryFieldSchema[]>([]);

const queryFilter: Readable<WireExpression | undefined> = derived(
    [filterSet, fieldSchemas],
    ([$filterSet, $fieldSchemas]) => svarToQueryFilter($filterSet, $fieldSchemas)
);

export function useQueryBuilderFilter() {
    function updateFilterSet(set: IFilterSet | null) {
        filterSet.set(set);
    }

    function updateFieldSchemas(schemas: QueryFieldSchema[]) {
        fieldSchemas.set(schemas);
    }

    function clearFilter() {
        filterSet.set(null);
    }

    return { filterSet, fieldSchemas, queryFilter, updateFilterSet, updateFieldSchemas, clearFilter };
}
