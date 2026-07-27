import { createQuery } from '@tanstack/svelte-query';
import type { ImageFilter, MetadataValueCountsView } from '$lib/api/lightly_studio_local';
import { getMetadataValueCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getMetadataValueCounts } from '$lib/api/lightly_studio_local/sdk.gen';

export type CategoricalMetadataBucket = {
    id: string;
    kind: 'value';
    value: string | boolean;
    label: string;
    count: number;
};

const valueBucketId = (value: string | boolean): string =>
    JSON.stringify(['value', typeof value, value]);

export const selectCategoricalDistributions = (
    response: Record<string, MetadataValueCountsView> | undefined
): Record<string, CategoricalMetadataBucket[]> =>
    Object.fromEntries(
        Object.entries(response ?? {}).map(([key, counts]) => {
            const buckets: CategoricalMetadataBucket[] = counts.value_counts.map(
                ({ value, count }) => ({
                    id: valueBucketId(value),
                    kind: 'value',
                    value,
                    label: String(value),
                    count
                })
            );
            return [key, buckets];
        })
    );

export interface CategoricalMetadataDistributionOptions {
    collectionId: string;
    filter?: ImageFilter;
}

export const getCategoricalMetadataDistributionRequestOptions = ({
    collectionId,
    filter
}: CategoricalMetadataDistributionOptions) => ({
    path: { collection_id: collectionId },
    ...(filter ? { body: { filters: filter } } : {})
});

export const useCategoricalMetadataDistribution = (
    getOptions: () => CategoricalMetadataDistributionOptions & { enabled?: boolean }
) =>
    createQuery(() => {
        const { collectionId, filter, enabled = true } = getOptions();
        const requestOptions = getCategoricalMetadataDistributionRequestOptions({
            collectionId,
            filter
        });
        return {
            ...getMetadataValueCountsOptions(requestOptions),
            enabled,
            select: selectCategoricalDistributions,
            placeholderData: (previous: Record<string, MetadataValueCountsView> | undefined) =>
                previous,
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await getMetadataValueCounts({
                    ...requestOptions,
                    signal,
                    throwOnError: true
                });
                return data;
            }
        };
    });
