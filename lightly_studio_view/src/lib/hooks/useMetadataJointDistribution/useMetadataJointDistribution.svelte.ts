import { createQuery } from '@tanstack/svelte-query';
import type {
    MetadataJointDistributionRequest,
    MetadataJointDistributionView
} from '$lib/api/lightly_studio_local';
import { getMetadataJointDistributionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getMetadataJointDistribution } from '$lib/api/lightly_studio_local/sdk.gen';

/** An image or video filter, tagged with its `filter_type`. */
type MetadataJointDistributionFilter = NonNullable<MetadataJointDistributionRequest['filters']>;

export interface MetadataJointDistributionOptions {
    collectionId: string;
    xKey: string;
    yKey: string;
    binCount: number;
    filter?: MetadataJointDistributionFilter;
}

/**
 * Removes the metadata filters of the given keys. The server ignores the filters of
 * the two axis keys, and keeping them in the request would refetch the same counts
 * after each cell selection.
 */
export const withoutMetadataKeyFilters = (
    filter: MetadataJointDistributionFilter,
    keys: string[]
): MetadataJointDistributionFilter => {
    const metadataFilters = filter.sample_filter?.metadata_filters;
    if (!metadataFilters) return filter;
    return {
        ...filter,
        sample_filter: {
            ...filter.sample_filter,
            metadata_filters: metadataFilters.filter(({ key }) => !keys.includes(key))
        }
    };
};

export const getMetadataJointDistributionRequestOptions = ({
    collectionId,
    xKey,
    yKey,
    binCount,
    filter
}: MetadataJointDistributionOptions) => ({
    path: { collection_id: collectionId },
    body: {
        x_key: xKey,
        y_key: yKey,
        bin_count: binCount,
        ...(filter ? { filters: withoutMetadataKeyFilters(filter, [xKey, yKey]) } : {})
    }
});

export const useMetadataJointDistribution = (
    getOptions: () => MetadataJointDistributionOptions & { enabled?: boolean }
) =>
    createQuery(() => {
        const { enabled = true, ...options } = getOptions();
        const requestOptions = getMetadataJointDistributionRequestOptions(options);
        return {
            ...getMetadataJointDistributionOptions(requestOptions),
            enabled,
            // Keep the previous heatmap while the counts refresh, but not after an axis
            // key changes: the old cells would show under the new axis labels.
            placeholderData: (previous: MetadataJointDistributionView | undefined) =>
                previous?.x_axis.key === options.xKey && previous.y_axis.key === options.yKey
                    ? previous
                    : undefined,
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await getMetadataJointDistribution({
                    ...requestOptions,
                    signal,
                    throwOnError: true
                });
                return data;
            }
        };
    });
