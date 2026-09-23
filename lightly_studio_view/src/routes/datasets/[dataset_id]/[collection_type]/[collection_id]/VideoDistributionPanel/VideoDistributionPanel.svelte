<script lang="ts">
    import DatasetDistributionPanel from '$lib/components/DatasetDistributionPanel/DatasetDistributionPanel.svelte';
    import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';
    import type { CategoryCount } from '$lib/components/BarChart';
    import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local/types.gen';
    import { useCategoricalMetadataDistribution, useNumericMetadataDistribution } from '$lib/hooks';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';
    import { useVideoAnnotationCounts } from '$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { buildDistributionSources } from '../distributionSources';
    import {
        selectHistogramRange,
        selectVideoDistributionBaseFilter,
        toCategoryCounts,
        toggleCategoricalValue,
        withoutCategoricalValues
    } from '../distributionHandlers';
    import {
        buildMetadataDistributionSource,
        selectCategoricalMetadataKeys,
        selectNumericMetadataKeys
    } from '../metadataDistributionSource';

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

    // With every annotation source unchecked, the class distribution has nothing to show.
    const toVisibleCategoryCounts = (countsData: unknown[] | undefined) =>
        $allSourcesHidden ? [] : toCategoryCounts(countsData, selectedClassNames);

    // One count query per group. The "All types" group counts every annotation type.
    const classCountGroups = [
        { id: 'all', label: 'All types', annotationType: undefined },
        {
            id: AnnotationType.CLASSIFICATION,
            label: 'Classification',
            annotationType: AnnotationType.CLASSIFICATION
        },
        {
            id: AnnotationType.OBJECT_DETECTION,
            label: 'Object detection',
            annotationType: AnnotationType.OBJECT_DETECTION
        },
        {
            id: AnnotationType.SEGMENTATION_MASK,
            label: 'Segmentation',
            annotationType: AnnotationType.SEGMENTATION_MASK
        }
    ].map(({ id, label, annotationType }) => ({
        id,
        label,
        query: useVideoAnnotationCounts(() => ({
            collectionId,
            filter,
            annotationType,
            enabled: !$allSourcesHidden
        }))
    }));

    // Class labels: one source, annotation types as groups. The counts are videos, not
    // annotations: a video counts once for each class that it or its frames contain.
    const classDistributionSource = $derived.by<DistributionSource>(() => {
        const base = {
            id: 'classes',
            label: 'Annotation classes',
            groupLabel: 'Annotation type',
            valueNoun: 'videos'
        };
        const [allTypesGroup, ...perTypeGroups] = classCountGroups.map(({ id, label, query }) => ({
            id,
            label,
            loading: query.isFetching,
            data: toVisibleCategoryCounts(query.data)
        }));
        // Skip types with no matches in the current view so the picker stays clean.
        const typeGroups = perTypeGroups.filter((group) => group.data.length > 0);
        // With zero or one populated type, "All types" would just duplicate it —
        // drop the group picker entirely.
        if (typeGroups.length <= 1) {
            return { ...base, loading: allTypesGroup.loading, data: allTypesGroup.data };
        }
        return { ...base, groups: [allTypesGroup, ...typeGroups] };
    });

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
            categoricalError: categoricalMetadataQuery.error?.message
        })
    );

    const distributionSources = $derived<DistributionSource[]>(
        buildDistributionSources({
            classSource: classDistributionSource,
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
    onCategoricalRetry={() => categoricalMetadataQuery.refetch()}
    {histogramBinCount}
    onHistogramBinCountChange={(binCount) => (histogramBinCount = binCount)}
    onGroupChange={(sourceId, groupId) => {
        activeDistributionSourceId = sourceId;
        activeDistributionGroupId = groupId;
    }}
/>
