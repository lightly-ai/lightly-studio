import { fromStore } from 'svelte/store';
import type { VideoFilter } from '$lib/api/lightly_studio_local';
import {
    useCategoricalMetadataDistribution,
    useMetadataFilters,
    useNumericMetadataDistribution
} from '$lib/hooks';
import {
    selectHistogramRange,
    toggleCategoricalValue,
    withoutCategoricalValues
} from '../distributionHandlers';
import {
    buildMetadataDistributionSource,
    selectCategoricalFetchState,
    selectCategoricalMetadataKeys,
    selectNumericMetadataKeys
} from '../metadataDistributionSource';

type MetadataFilter = (VideoFilter & { filter_type: 'video' }) | undefined;

interface UseVideoMetadataDistributionSourceParams {
    collectionId: string;
    /** The filter of the videos grid, with every sidebar filter applied. */
    filter: MetadataFilter;
    /** Only the tags and sample ids of the grid, so the totals stay stable. */
    baseFilter: MetadataFilter;
    histogramBinCount: number;
    /** The source and group that the panel shows. Only the shown metadata key is fetched. */
    activeSourceId: string | undefined;
    activeGroupId: string | undefined;
}

/**
 * Builds the metadata source of the video distribution panel, and the handlers that turn
 * clicks on its bars into sidebar metadata filters.
 */
export function useVideoMetadataDistributionSource(
    getParams: () => UseVideoMetadataDistributionSourceParams
) {
    const {
        metadataValues,
        metadataBounds,
        metadataInfo,
        categoricalMetadataValues,
        updateMetadataValues,
        updateCategoricalMetadataValues
    } = useMetadataFilters();
    const ranges = fromStore(metadataValues);
    const bounds = fromStore(metadataBounds);
    const info = fromStore(metadataInfo);
    const values = fromStore(categoricalMetadataValues);

    const numericKeys = $derived(selectNumericMetadataKeys(info.current));
    const categoricalKeys = $derived(selectCategoricalMetadataKeys(info.current));
    const activeField = $derived.by<{ name: string; type: 'numeric' | 'categorical' } | undefined>(
        () => {
            const { activeSourceId, activeGroupId } = getParams();
            if (activeSourceId !== 'metadata' || activeGroupId === undefined) {
                return undefined;
            }
            if (categoricalKeys.includes(activeGroupId)) {
                return { name: activeGroupId, type: 'categorical' };
            }
            if (numericKeys.includes(activeGroupId)) {
                return { name: activeGroupId, type: 'numeric' };
            }
            return undefined;
        }
    );
    const categoricalField = $derived(
        activeField?.type === 'categorical' ? activeField.name : undefined
    );

    // Bin edges and counts both span the grid scope (baseFilter), so the bars stay
    // stable while the user changes the sidebar filters.
    const histogramsQuery = useNumericMetadataDistribution(() => {
        const { collectionId, baseFilter, histogramBinCount } = getParams();
        return {
            collectionId,
            filter: baseFilter,
            binCount: histogramBinCount,
            fields: activeField?.type === 'numeric' ? [activeField.name] : undefined,
            enabled: activeField?.type === 'numeric'
        };
    });
    const categoricalQueryParams = (filter: MetadataFilter) => ({
        collectionId: getParams().collectionId,
        filter,
        fields: categoricalField === undefined ? undefined : [categoricalField],
        enabled: categoricalField !== undefined
    });
    const categoricalQuery = useCategoricalMetadataDistribution(() =>
        categoricalQueryParams(getParams().baseFilter)
    );
    // The same counts with every sidebar filter applied, for the coloured foreground bars.
    const categoricalFilteredQuery = useCategoricalMetadataDistribution(() =>
        categoricalQueryParams(getParams().filter)
    );

    const source = $derived.by(() => {
        const categoricalFetchState = selectCategoricalFetchState(
            [categoricalQuery, categoricalFilteredQuery],
            categoricalField
        );
        return buildMetadataDistributionSource({
            histograms: histogramsQuery.data ?? {},
            numericKeys,
            categoricalKeys,
            categorical: categoricalQuery.data ?? {},
            // Keep undefined while loading, so the panel waits for the filtered bars.
            filteredCategorical: categoricalFilteredQuery.data,
            selectedRanges: ranges.current,
            selectedValues: values.current,
            tagDistributions: [],
            valueNoun: 'videos',
            numericLoading: histogramsQuery.isFetching,
            categoricalLoading: categoricalFetchState.loading,
            categoricalUpdating: categoricalFetchState.updating,
            // The filtered query draws the foreground bars, so its failure must show too.
            categoricalError: (categoricalQuery.error ?? categoricalFilteredQuery.error)?.message
        });
    });

    return {
        get source() {
            return source;
        },
        onHistogramRangeSelect: (metadataKey: string, range: { min: number; max: number }) => {
            const bound = bounds.current[metadataKey];
            if (!bound) return;
            updateMetadataValues({
                ...ranges.current,
                [metadataKey]: selectHistogramRange({
                    bound,
                    current: ranges.current[metadataKey],
                    range
                })
            });
        },
        onCategoricalValueToggle: (metadataKey: string, value: string | boolean | null) => {
            updateCategoricalMetadataValues({
                ...values.current,
                [metadataKey]: toggleCategoricalValue(values.current[metadataKey] ?? [], value)
            });
        },
        onCategoricalValuesClear: (metadataKey: string) => {
            updateCategoricalMetadataValues(withoutCategoricalValues(values.current, metadataKey));
        },
        onCategoricalRetry: () => {
            categoricalQuery.refetch();
            categoricalFilteredQuery.refetch();
        }
    };
}
