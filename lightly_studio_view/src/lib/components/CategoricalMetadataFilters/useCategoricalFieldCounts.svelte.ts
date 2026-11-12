import { validate as validateUUID } from 'uuid';
import { useCategoricalMetadataDistribution } from '$lib/hooks';
import type { MetadataValueCountsFilter } from '$lib/hooks/useCategoricalMetadataDistribution/useCategoricalMetadataDistribution.svelte';
import { withAllValues } from './withAllValues';

interface Options {
    collectionId: string;
    /** Tagged image or video filter. `undefined` means no filter. */
    filter?: MetadataValueCountsFilter;
    /** Only these fields are requested; none means no request. */
    fields: string[];
}

export function useCategoricalFieldCounts(getOptions: () => Options) {
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
        return Object.fromEntries(
            Object.entries(filtered).map(([field, buckets]) => [
                field,
                withAllValues(buckets, all[field] ?? [])
            ])
        );
    });
    const loading = $derived(query.isFetching && (query.isLoading || query.isPlaceholderData));
    const updating = $derived(query.isFetching && !query.isLoading);
    const error = $derived(query.error?.message);

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
        refetch: () => {
            query.refetch();
        }
    };
}
