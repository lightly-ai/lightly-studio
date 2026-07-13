import { exportCollectionStats, type ImageFilter } from '$lib/api/lightly_studio_local';
import type { ExportFilter } from '$lib/services/types';
import { writable, type Readable } from 'svelte/store';

interface UseExportSamplesCountProps {
    collection_id: string;
    includeFilter?: ExportFilter;
    excludeFilter?: ExportFilter;
    collectionFilter?: ImageFilter | null;
}

interface UseExportSamplesCountReturn {
    isLoading: Readable<boolean>;
    error: Readable<string | undefined>;
    count: Readable<number>;
}

/**
 * Hook for exporting collection data with filters
 * @param params Export parameters including collection_id and filters
 * @returns Object containing export state and trigger function
 */
export function useExportSamplesCount({
    collection_id,
    includeFilter,
    excludeFilter,
    collectionFilter
}: UseExportSamplesCountProps): UseExportSamplesCountReturn {
    const count = writable(0);
    const error = writable<string | undefined>(undefined);
    const isLoading = writable(false);

    const hasIncludeFilter = includeFilter && Object.keys(includeFilter).length > 0;
    const hasExcludeFilter = excludeFilter && Object.keys(excludeFilter).length > 0;
    const hasCollectionFilter = collectionFilter != null;
    if (hasIncludeFilter || hasExcludeFilter || hasCollectionFilter) {
        isLoading.set(true);

        exportCollectionStats({
            path: { collection_id },
            body: {
                include: includeFilter,
                exclude: excludeFilter,
                collection_filter: collectionFilter
            }
        })
            .then((response) => {
                if (response?.data) {
                    count.set(response.data);
                }
            })
            .catch((_error) => {
                error.set(_error.message);
            })
            .finally(() => {
                isLoading.set(false);
            });
    }

    return {
        isLoading,
        error,
        count
    };
}
