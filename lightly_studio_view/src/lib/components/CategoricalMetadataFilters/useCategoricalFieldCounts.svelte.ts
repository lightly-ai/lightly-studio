import { validate as validateUUID } from 'uuid';
import { useCategoricalMetadataDistribution } from '$lib/hooks';
import type { MetadataValueCountsFilter } from '$lib/hooks/useCategoricalMetadataDistribution/useCategoricalMetadataDistribution.svelte';
import { getErrorMessage } from '$lib/utils';

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
    const distributions = $derived(query.data ?? {});
    const loading = $derived(query.isFetching && (query.isLoading || query.isPlaceholderData));
    const updating = $derived(query.isFetching && !query.isLoading);
    const error = $derived(getErrorMessage(query.error));

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
