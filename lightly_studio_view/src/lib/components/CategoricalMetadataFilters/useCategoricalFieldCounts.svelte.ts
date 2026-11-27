import { validate as validateUUID } from 'uuid';
import { useCategoricalMetadataDistribution, type MetadataValueCountsFilter } from '$lib/hooks';
import { withAllValues } from './withAllValues';

interface Options {
    collectionId: string;
    /** Tagged image or video filter. `undefined` means no filter. */
    filter?: MetadataValueCountsFilter;
    /** Only these fields are requested; none means no request. */
    fields: string[];
}

export interface UseCategoricalFieldCountsReturn {
    /** Value counts per field, including values outside the filter with a count of 0. */
    readonly distributions: Record<string, ReturnType<typeof withAllValues>>;
    readonly loading: boolean;
    readonly updating: boolean;
    readonly error: string | undefined;
    /** `true` once every value of the fields is known, so a total can be shown. */
    readonly allValuesLoaded: boolean;
    refetch: () => void;
}

export function useCategoricalFieldCounts(
    getOptions: () => Options
): UseCategoricalFieldCountsReturn {
    const query = useCategoricalMetadataDistribution(() => {
        const { collectionId, filter, fields } = getOptions();
        return {
            collectionId,
            filter,
            fields,
            enabled: validateUUID(collectionId) && fields.length > 0
        };
    });
    // Lists every value of each field; `query` only provides the counts. Without a filter,
    // `query` already lists every value.
    const allValuesQuery = useCategoricalMetadataDistribution(() => {
        const { collectionId, filter, fields } = getOptions();
        return {
            collectionId,
            filter: filter && { filter_type: filter.filter_type },
            fields,
            enabled: validateUUID(collectionId) && fields.length > 0 && filter !== undefined
        };
    });
    const distributions = $derived.by(() => {
        const filtered = query.data ?? {};
        const all = allValuesQuery.data ?? {};
        // A field only in `all` still lists its values, e.g. when the filtered request fails.
        const fields = new Set([...Object.keys(filtered), ...Object.keys(all)]);
        return Object.fromEntries(
            [...fields].map((field) => [
                field,
                withAllValues(filtered[field] ?? [], all[field] ?? [])
            ])
        );
    });
    const loading = $derived(query.isFetching && (query.isLoading || query.isPlaceholderData));
    const updating = $derived(query.isFetching && !query.isLoading);
    const error = $derived(query.error?.message);
    // Without a filter, `query` already lists every value.
    const allValuesLoaded = $derived(
        getOptions().filter === undefined || allValuesQuery.data !== undefined
    );

    return {
        get distributions() {
            return distributions;
        },
        get loading() {
            return loading;
        },
        get updating() {
            return updating;
        },
        get error() {
            return error;
        },
        get allValuesLoaded() {
            return allValuesLoaded;
        },
        refetch: () => {
            query.refetch();
        }
    };
}
