import { createQuery } from '@tanstack/svelte-query';
import type { HistogramView, ImageFilter } from '$lib/api/lightly_studio_local';
import { getImageHistogramsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getImageHistograms } from '$lib/api/lightly_studio_local/sdk.gen';
import type { HistogramData } from '$lib/components/Histogram';
import { selectDistributions } from '$lib/hooks/useNumericMetadataDistribution';

/** An image field with a histogram, as the backend names it. */
export type ImageField = 'width' | 'height';

export const IMAGE_FIELDS: ImageField[] = ['width', 'height'];

const IMAGE_FIELD_ID_PREFIX = 'image:';

/**
 * The distribution group ID of an image field. The prefix keeps it apart from a user
 * metadata key with the same name.
 */
export const toImageFieldId = (field: ImageField): string => `${IMAGE_FIELD_ID_PREFIX}${field}`;

/** The image field of a distribution group ID, or undefined for other groups. */
export const fromImageFieldId = (id: string): ImageField | undefined =>
    IMAGE_FIELDS.find((field) => toImageFieldId(field) === id);

/** Maps the endpoint response to histograms keyed by distribution group ID. */
export const selectImageFieldDistributions = (
    histograms: Record<string, HistogramView> | undefined
): Record<string, HistogramData> =>
    Object.fromEntries(
        Object.entries(selectDistributions(histograms)).map(([field, histogram]) => [
            `${IMAGE_FIELD_ID_PREFIX}${field}`,
            histogram
        ])
    );

export interface ImageFieldDistributionOptions {
    collectionId: string;
    filter?: ImageFilter;
    /** Number of equal-width bins per histogram (server default: 20). */
    binCount?: number;
    fields?: ImageField[];
}

export const getImageFieldHistogramRequestOptions = ({
    collectionId,
    filter,
    binCount,
    fields
}: ImageFieldDistributionOptions) => ({
    path: { collection_id: collectionId },
    body: {
        ...(filter ? { filters: filter } : {}),
        ...(binCount ? { bin_count: binCount } : {}),
        ...(fields ? { fields } : {})
    }
});

/**
 * Queries the value-distribution histograms of the image width and height, keyed by
 * distribution group ID (see {@link toImageFieldId}).
 *
 * The bins come from `POST /collections/{id}/images/histograms`. Bin edges span the full
 * collection, and the counts follow the given filter.
 */
export const useImageFieldDistribution = (
    getOptions: () => ImageFieldDistributionOptions & { enabled?: boolean }
) =>
    createQuery(() => {
        const { enabled = true, ...options } = getOptions();
        const requestOptions = getImageFieldHistogramRequestOptions(options);
        return {
            ...getImageHistogramsOptions(requestOptions),
            enabled,
            select: selectImageFieldDistributions,
            // Keep the previous bars on screen while a filter change refetches.
            placeholderData: (previous: Record<string, HistogramView> | undefined) => previous,
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await getImageHistograms({
                    ...requestOptions,
                    signal,
                    throwOnError: true
                });
                return data;
            }
        };
    });
