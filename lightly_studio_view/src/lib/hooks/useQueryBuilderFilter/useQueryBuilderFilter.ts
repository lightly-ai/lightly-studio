import { writable, derived, type Readable } from 'svelte/store';
import { svarToQueryFilter } from '$lib/utils/svarToQueryFilter';
import type { IFilterSet } from '$lib/types/svar-filter';
import type { components } from '$lib/schema';
type QueryFieldSchema = components['schemas']['QueryFieldSchema'];
type WireExpression = components['schemas']['WireField'] | components['schemas']['WireTagsContains'] | components['schemas']['WireAnd'] | components['schemas']['WireOr'] | components['schemas']['WireNot'];

// Module-level singletons so the layout panel and the samples page share state.
const filterSet = writable<IFilterSet | null>(null);
const fieldSchemas = writable<QueryFieldSchema[]>([]);
const pythonQuery = writable<string | null>(null);

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

    function updatePythonQuery(query: string | null) {
        pythonQuery.set(query);
    }

    function clearFilter() {
        filterSet.set(null);
        pythonQuery.set(null);
    }

    return { filterSet, fieldSchemas, queryFilter, pythonQuery, updateFilterSet, updateFieldSchemas, updatePythonQuery, clearFilter };
}
