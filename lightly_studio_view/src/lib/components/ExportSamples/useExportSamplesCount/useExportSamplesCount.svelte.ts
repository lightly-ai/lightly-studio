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

export function useExportSamplesCount(
    getProps: () => UseExportSamplesCountProps
): UseExportSamplesCountReturn {
    const count = writable(0);
    const error = writable<string | undefined>(undefined);
    const isLoading = writable(false);

    $effect(() => {
        const { collection_id, includeFilter, excludeFilter, collectionFilter } = getProps();

        const hasIncludeFilter = includeFilter != null && Object.keys(includeFilter).length > 0;
        const hasExcludeFilter = excludeFilter != null && Object.keys(excludeFilter).length > 0;
        const hasCollectionFilter = collectionFilter != null;

        if (!hasIncludeFilter && !hasExcludeFilter && !hasCollectionFilter) {
            isLoading.set(false);
            error.set(undefined);
            count.set(0);
            return;
        }

        const controller = new AbortController();

        isLoading.set(true);
        error.set(undefined);

        exportCollectionStats({
            path: { collection_id },
            body: {
                include: includeFilter,
                exclude: excludeFilter,
                collection_filter: collectionFilter
            },
            signal: controller.signal
        })
            .then((response) => {
                if (!controller.signal.aborted && response?.data != null) {
                    count.set(response.data);
                }
            })
            .catch((_error) => {
                if (!controller.signal.aborted) {
                    error.set(_error.message);
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    isLoading.set(false);
                }
            });

        return () => controller.abort();
    });

    return { isLoading, error, count };
}
