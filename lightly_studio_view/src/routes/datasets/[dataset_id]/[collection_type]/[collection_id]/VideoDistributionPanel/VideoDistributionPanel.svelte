<script lang="ts">
    import DatasetDistributionPanel from '$lib/components/DatasetDistributionPanel/DatasetDistributionPanel.svelte';
    import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';
    import type { CategoryCount } from '$lib/components/BarChart';
    import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
    import { useCategoricalMetadataDistribution, useNumericMetadataDistribution } from '$lib/hooks';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { buildDistributionSources } from '../distributionSources';
    import {
        selectHistogramRange,
        selectVideoDistributionBaseFilter,
        toggleCategoricalValue,
        withoutCategoricalValues
    } from '../distributionHandlers';
    import {
        buildMetadataDistributionSource,
        selectCategoricalMetadataKeys,
        selectNumericMetadataKeys
    } from '../metadataDistributionSource';
    import { useVideoClassDistributionSource } from './useVideoClassDistributionSource.svelte';

    interface Props {
        collectionId: string;
        /** False only when annotation labels have loaded and there are none. */
        hasAnnotationClasses: boolean;
        /** Labels selected in the sidebar's LabelsMenu. */
        selectedClassNames: string[];
        onClassBarClick: (item: CategoryCount) => void;
        onClose: () => void;
        // The host keeps the bin count so that it stays when the panel closes and opens again.
        histogramBinCount: number;
    }

    let {
        collectionId,
        hasAnnotationClasses,
        selectedClassNames,
        onClassBarClick,
        onClose,
        histogramBinCount = $bindable()
    }: Props = $props();

    const {
        metadataValues,
        metadataBounds,
        metadataInfo,
        categoricalMetadataValues,
        updateMetadataValues,
        updateCategoricalMetadataValues
    } = useMetadataFilters();
    const { allSourcesHidden } = useAnnotationCollectionsFilter();
    const { videoFilter } = useVideoFilters();

    // The filter of the videos grid, with every sidebar filter applied.
    const filter = $derived(
        $videoFilter ? { ...$videoFilter, filter_type: 'video' as const } : undefined
    );
    // Only the tags and sample ids of the grid, so the totals stay stable.
    const baseFilter = $derived(selectVideoDistributionBaseFilter($videoFilter));

    let activeDistributionSourceId = $state<string | undefined>(undefined);
    let activeDistributionGroupId = $state<string | undefined>(undefined);

    const classDistribution = useVideoClassDistributionSource(() => ({
        collectionId,
        filter,
        selectedClassNames,
        allSourcesHidden: $allSourcesHidden
    }));

    const numericMetadataKeys = $derived(selectNumericMetadataKeys($metadataInfo));
    const categoricalMetadataKeys = $derived(selectCategoricalMetadataKeys($metadataInfo));
    const activeMetadataField = $derived.by<
        { name: string; type: 'numeric' | 'categorical' } | undefined
    >(() => {
        if (activeDistributionSourceId !== 'metadata' || activeDistributionGroupId === undefined) {
            return undefined;
        }
        if (categoricalMetadataKeys.includes(activeDistributionGroupId)) {
            return { name: activeDistributionGroupId, type: 'categorical' };
        }
        if (numericMetadataKeys.includes(activeDistributionGroupId)) {
            return { name: activeDistributionGroupId, type: 'numeric' };
        }
        return undefined;
    });

    // Bin edges and counts both span the grid scope (baseFilter), so the bars stay
    // stable while the user changes the sidebar filters.
    const metadataHistogramsQuery = useNumericMetadataDistribution(() => ({
        collectionId,
        filter: baseFilter,
        binCount: histogramBinCount,
        fields: activeMetadataField?.type === 'numeric' ? [activeMetadataField.name] : undefined,
        enabled: activeMetadataField?.type === 'numeric'
    }));

    const categoricalFields = $derived(
        activeMetadataField?.type === 'categorical' ? [activeMetadataField.name] : undefined
    );
    const categoricalMetadataQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter: baseFilter,
        fields: categoricalFields,
        enabled: activeMetadataField?.type === 'categorical'
    }));
    // The same counts with every sidebar filter applied, for the coloured foreground bars.
    const categoricalMetadataFilteredQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter,
        fields: categoricalFields,
        enabled: activeMetadataField?.type === 'categorical'
    }));

    const metadataDistributionSource = $derived(
        buildMetadataDistributionSource({
            histograms: metadataHistogramsQuery.data ?? {},
            numericKeys: numericMetadataKeys,
            categoricalKeys: categoricalMetadataKeys,
            categorical: categoricalMetadataQuery.data ?? {},
            // Keep undefined while loading, so the panel waits for the filtered bars.
            filteredCategorical: categoricalMetadataFilteredQuery.data,
            selectedRanges: $metadataValues,
            selectedValues: $categoricalMetadataValues,
            tagDistributions: [],
            numericLoading: metadataHistogramsQuery.isFetching,
            categoricalLoading:
                categoricalMetadataQuery.isFetching || categoricalMetadataFilteredQuery.isFetching,
            // The filtered query draws the foreground bars, so its failure must show too.
            categoricalError: (
                categoricalMetadataQuery.error ?? categoricalMetadataFilteredQuery.error
            )?.message
        })
    );

    const distributionSources = $derived<DistributionSource[]>(
        buildDistributionSources({
            classSource: classDistribution.source,
            metadataSource: metadataDistributionSource,
            hasAnnotationClasses
        })
    );

    const handleHistogramRangeSelect = (
        metadataKey: string,
        range: { min: number; max: number }
    ) => {
        const bound = $metadataBounds[metadataKey];
        if (!bound) return;
        updateMetadataValues({
            ...$metadataValues,
            [metadataKey]: selectHistogramRange({
                bound,
                current: $metadataValues[metadataKey],
                range
            })
        });
    };

    const handleCategoricalValueToggle = (metadataKey: string, value: string | boolean | null) => {
        updateCategoricalMetadataValues({
            ...$categoricalMetadataValues,
            [metadataKey]: toggleCategoricalValue(
                $categoricalMetadataValues[metadataKey] ?? [],
                value
            )
        });
    };
</script>

<!-- Video counts support only the samples count mode, so the panel hides the count mode select. -->
<DatasetDistributionPanel
    sources={distributionSources}
    initialCountMode={AnnotationCountMode.SAMPLES}
    showCountMode={false}
    {onClose}
    onBarClick={onClassBarClick}
    onHistogramRangeSelect={handleHistogramRangeSelect}
    onCategoricalValueToggle={handleCategoricalValueToggle}
    onCategoricalValuesClear={(metadataKey) =>
        updateCategoricalMetadataValues(
            withoutCategoricalValues($categoricalMetadataValues, metadataKey)
        )}
    onCategoricalRetry={() => {
        categoricalMetadataQuery.refetch();
        categoricalMetadataFilteredQuery.refetch();
    }}
    {histogramBinCount}
    onHistogramBinCountChange={(binCount) => (histogramBinCount = binCount)}
    onGroupChange={(sourceId, groupId) => {
        activeDistributionSourceId = sourceId;
        activeDistributionGroupId = groupId;
    }}
/>
