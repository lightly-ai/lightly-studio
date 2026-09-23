<script lang="ts">
    import DatasetDistributionPanel from '$lib/components/DatasetDistributionPanel/DatasetDistributionPanel.svelte';
    import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';
    import type { CategoryCount } from '$lib/components/BarChart';
    import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local/types.gen';
    import {
        useCategoricalMetadataDistribution,
        useImageAnnotationCounts,
        useImageAnnotationCountsBySampleTags,
        useImageAnnotationCountsQueryKey,
        useMetadataDistributionsBySampleTags,
        useNumericMetadataDistribution,
        useTags
    } from '$lib/hooks';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';
    import { buildImageFilter } from '$lib/utils/buildImageFilter';
    import { buildDistributionSources } from '../distributionSources';
    import {
        selectHistogramRange,
        toCategoryCounts,
        toggleCategoricalValue,
        withoutCategoricalValues
    } from '../distributionHandlers';
    import {
        buildMetadataDistributionSource,
        selectCategoricalMetadataKeys,
        selectComparisonSampleTags,
        selectNumericMetadataKeys
    } from '../metadataDistributionSource';

    type ImageDistributionFilter = ReturnType<typeof buildImageFilter>;

    interface Props {
        collectionId: string;
        datasetId: string;
        /** The full sidebar filter. The labels filter counts use the same filter. */
        filter: ImageDistributionFilter;
        /** Class counts of the labels filter, shown while the distribution counts load. */
        annotationCounts: unknown[] | undefined;
        /** False only when annotation labels have loaded and there are none. */
        hasAnnotationClasses: boolean;
        /** Labels selected in the sidebar's LabelsMenu. */
        selectedClassNames: string[];
        onClassBarClick: (item: CategoryCount) => void;
        onClose: () => void;
        // The host keeps these settings so that they stay when the panel closes and opens again.
        countMode: AnnotationCountMode;
        histogramBinCount: number;
        comparisonTagIds: string[];
    }

    let {
        collectionId,
        datasetId,
        filter,
        annotationCounts,
        hasAnnotationClasses,
        selectedClassNames,
        onClassBarClick,
        onClose,
        countMode = $bindable(),
        histogramBinCount = $bindable(),
        comparisonTagIds = $bindable()
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
    const { imageFilter } = useImageFilters();

    // Distribution queries always show the full dataset so bar heights stay
    // stable as sidebar filters are applied.  Filtering is communicated through
    // bar colour (green = in selection, grey = out of selection) rather than
    // through shrinking bars, which loses the original distribution context.
    // Tag / sample / confusion-cell / query context is kept so the distributions
    // stay scoped to the collection the user is currently exploring.
    const distributionBaseFilter = $derived(
        buildImageFilter({
            dimensionsValues: null,
            annotationFilter: undefined,
            metadataFilters: undefined,
            sampleIds: $imageFilter?.sample_filter?.sample_ids ?? [],
            tagIds: $imageFilter?.sample_filter?.tag_ids ?? [],
            confusionCell: $imageFilter?.sample_filter?.confusion_cell ?? null,
            queryExpr: $imageFilter?.sample_filter?.query_expr ?? null
        })
    );

    // With every annotation source unchecked, the class distribution has nothing to show,
    // whichever count query it came from.
    const toVisibleCategoryCounts = (countsData: unknown[] | undefined) =>
        $allSourcesHidden ? [] : toCategoryCounts(countsData, selectedClassNames);

    const classDistributionCounts = $derived(toVisibleCategoryCounts(annotationCounts));

    // The class count queries skip the request while every annotation source is unchecked.
    const distributionCountsEnabled = $derived(!$allSourcesHidden);

    const { tags: distributionSampleTags } = $derived(
        useTags({ collection_id: datasetId, kind: ['sample'] })
    );
    const distributionSampleTagItems = $derived(
        $distributionSampleTags.map((tag) => ({
            value: tag.tag_id,
            label: tag.name,
            testId: `dataset-distribution-tag-option-${tag.tag_id}`
        }))
    );
    $effect(() => {
        const validIds = new Set($distributionSampleTags.map((tag) => tag.tag_id));
        const validSelection = comparisonTagIds.filter((id) => validIds.has(id));
        if (validSelection.length !== comparisonTagIds.length) {
            comparisonTagIds = validSelection;
        }
    });

    // The 'all' query uses a suffixed key so its cache entry is isolated from
    // the shared annotation counts query (labels filter). TanStack's prefix
    // matching ensures mutation invalidations still reach it.
    const distributionAllQueryKey = [...useImageAnnotationCountsQueryKey, 'distribution'];

    const distributionAllQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        filter,
        countMode,
        queryKey: distributionAllQueryKey,
        enabled: distributionCountsEnabled
    }));

    let activeDistributionSourceId = $state<string | undefined>(undefined);
    let activeDistributionGroupId = $state<string | undefined>(undefined);

    const distributionClassificationQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        annotationType: AnnotationType.CLASSIFICATION,
        filter,
        countMode,
        enabled: distributionCountsEnabled
    }));

    const distributionObjectDetectionQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        annotationType: AnnotationType.OBJECT_DETECTION,
        filter,
        countMode,
        enabled: distributionCountsEnabled
    }));

    const distributionSegmentationQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        annotationType: AnnotationType.SEGMENTATION_MASK,
        filter,
        countMode,
        enabled: distributionCountsEnabled
    }));

    const groupedCountsParams = (annotationType?: AnnotationType) => ({
        collectionId: datasetId,
        sampleTagIds: comparisonTagIds,
        filter,
        countMode,
        annotationType,
        enabled:
            activeDistributionSourceId === 'classes' &&
            comparisonTagIds.length > 0 &&
            (annotationType === undefined
                ? activeDistributionGroupId === undefined || activeDistributionGroupId === 'all'
                : activeDistributionGroupId === annotationType)
    });
    const distributionAllTagQuery = useImageAnnotationCountsBySampleTags(() =>
        groupedCountsParams()
    );
    const distributionClassificationTagQuery = useImageAnnotationCountsBySampleTags(() =>
        groupedCountsParams(AnnotationType.CLASSIFICATION)
    );
    const distributionObjectDetectionTagQuery = useImageAnnotationCountsBySampleTags(() =>
        groupedCountsParams(AnnotationType.OBJECT_DETECTION)
    );
    const distributionSegmentationTagQuery = useImageAnnotationCountsBySampleTags(() =>
        groupedCountsParams(AnnotationType.SEGMENTATION_MASK)
    );

    const classComparisonQueries: Record<
        string,
        ReturnType<typeof useImageAnnotationCountsBySampleTags>
    > = {
        all: distributionAllTagQuery,
        [AnnotationType.CLASSIFICATION]: distributionClassificationTagQuery,
        [AnnotationType.OBJECT_DETECTION]: distributionObjectDetectionTagQuery,
        [AnnotationType.SEGMENTATION_MASK]: distributionSegmentationTagQuery
    };
    const activeClassComparisonQuery = $derived(
        activeDistributionSourceId === 'classes'
            ? classComparisonQueries[activeDistributionGroupId ?? 'all']
            : undefined
    );

    // The panel's sources are the distribution *types* (class labels,
    // metadata, …); the subset within a type (annotation type, metadata key)
    // is the source's group, picked in a second, contextual dropdown.

    // Class labels: one source, annotation types as groups. The per-type
    // valueNoun from the count-mode work collapses to the source level: in
    // Samples mode everything counts samples, otherwise annotations.
    const classDistributionSource = $derived.by<DistributionSource>(() => {
        const base = {
            id: 'classes',
            label: 'Annotation classes',
            groupLabel: 'Annotation type',
            valueNoun: countMode === AnnotationCountMode.SAMPLES ? 'samples' : 'annotations',
            comparisonLoading: activeClassComparisonQuery?.isFetching,
            comparisonError: activeClassComparisonQuery?.error?.message
        };

        // Use the distribution-specific "all" query so the "All types" group
        // respects countMode. Fall back to the shared counts while the
        // distribution query is still loading (data === undefined).
        const allDistributionData =
            distributionAllQuery.data !== undefined
                ? toVisibleCategoryCounts(distributionAllQuery.data)
                : classDistributionCounts;
        const hasTagSelection = comparisonTagIds.length > 0;
        const comparisonAllData =
            hasTagSelection && !$allSourcesHidden ? distributionAllTagQuery.data : undefined;
        const allTypesGroup = {
            id: 'all',
            label: 'All types',
            loading: distributionAllQuery.isFetching,
            data: allDistributionData,
            comparisonData: comparisonAllData
        };

        const perType: {
            id: AnnotationType;
            label: string;
            query: ReturnType<typeof useImageAnnotationCounts>;
            comparisonQuery: ReturnType<typeof useImageAnnotationCountsBySampleTags>;
        }[] = [
            {
                id: AnnotationType.CLASSIFICATION,
                label: 'Classification',
                query: distributionClassificationQuery,
                comparisonQuery: distributionClassificationTagQuery
            },
            {
                id: AnnotationType.OBJECT_DETECTION,
                label: 'Object detection',
                query: distributionObjectDetectionQuery,
                comparisonQuery: distributionObjectDetectionTagQuery
            },
            {
                id: AnnotationType.SEGMENTATION_MASK,
                label: 'Segmentation',
                query: distributionSegmentationQuery,
                comparisonQuery: distributionSegmentationTagQuery
            }
        ];
        const typeGroups = perType
            .map(({ id, label, query, comparisonQuery }) => ({
                id,
                label,
                loading: query.isFetching,
                data: toVisibleCategoryCounts(query.data),
                comparisonData:
                    hasTagSelection && !$allSourcesHidden ? comparisonQuery.data : undefined
            }))
            // Skip types with no matches in the current view so the picker stays clean.
            .filter((group) => group.data.length > 0);
        // With zero or one populated type, "All types" would just duplicate it —
        // drop the group picker entirely.
        if (typeGroups.length <= 1)
            return {
                ...base,
                loading: distributionAllQuery.isFetching,
                data: allDistributionData,
                comparisonData: comparisonAllData
            };
        return { ...base, groups: [allTypesGroup, ...typeGroups] };
    });

    // Numeric metadata fields as histogram groups. Bin edges and counts both
    // span the full collection (distributionBaseFilter strips analysis filters)
    // so bar heights stay stable while the user adjusts sidebar filters.
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

    const metadataHistogramsQuery = useNumericMetadataDistribution(() => ({
        collectionId,
        filter: distributionBaseFilter,
        binCount: histogramBinCount,
        fields: activeMetadataField?.type === 'numeric' ? [activeMetadataField.name] : undefined,
        enabled: activeMetadataField?.type === 'numeric'
    }));
    // query.data is already Record<string, HistogramData> — the hook applies
    // selectDistributions internally via the TanStack Query `select` option.
    const metadataDistributions = $derived(metadataHistogramsQuery.data ?? {});

    const categoricalMetadataQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter: distributionBaseFilter,
        fields:
            activeMetadataField?.type === 'categorical' ? [activeMetadataField.name] : undefined,
        enabled: activeMetadataField?.type === 'categorical'
    }));
    const categoricalMetadataDistributions = $derived(categoricalMetadataQuery.data ?? {});

    // Second categorical query with the full sidebar filter applied.  Its counts
    // are passed as `filteredBuckets` so each bar can show a grey background at
    // the unfiltered height with a coloured foreground at the filtered height.
    const categoricalMetadataFilteredQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter,
        fields:
            activeMetadataField?.type === 'categorical' ? [activeMetadataField.name] : undefined,
        enabled: activeMetadataField?.type === 'categorical'
    }));
    // Keep undefined (not {}) while loading so DatasetDistributionPanel defers
    // rendering the background bars until the filtered data is ready.
    const categoricalMetadataFilteredDistributions = $derived(
        categoricalMetadataFilteredQuery.data
    );

    const selectedDistributionSampleTags = $derived(
        selectComparisonSampleTags(distributionSampleTagItems, comparisonTagIds)
    );
    const metadataTagDistributionsQuery = useMetadataDistributionsBySampleTags(() => ({
        collectionId,
        sampleTags: selectedDistributionSampleTags,
        filter: distributionBaseFilter,
        binCount: histogramBinCount,
        field: activeMetadataField,
        enabled: true
    }));
    const metadataTagDistributions = $derived(metadataTagDistributionsQuery.data ?? []);
    const metadataDistributionSource = $derived(
        buildMetadataDistributionSource({
            histograms: metadataDistributions,
            numericKeys: numericMetadataKeys,
            categoricalKeys: categoricalMetadataKeys,
            categorical: categoricalMetadataDistributions,
            filteredCategorical: categoricalMetadataFilteredDistributions,
            selectedRanges: $metadataValues,
            selectedValues: $categoricalMetadataValues,
            tagDistributions: metadataTagDistributions,
            numericLoading: metadataHistogramsQuery.isFetching,
            categoricalLoading:
                (categoricalMetadataQuery.isFetching &&
                    (categoricalMetadataQuery.isLoading ||
                        categoricalMetadataQuery.isPlaceholderData)) ||
                (categoricalMetadataFilteredQuery.isFetching &&
                    (categoricalMetadataFilteredQuery.isLoading ||
                        categoricalMetadataFilteredQuery.isPlaceholderData)),
            categoricalUpdating:
                (categoricalMetadataQuery.isFetching &&
                    !categoricalMetadataQuery.isLoading &&
                    !categoricalMetadataQuery.isPlaceholderData) ||
                (categoricalMetadataFilteredQuery.isFetching &&
                    !categoricalMetadataFilteredQuery.isLoading &&
                    !categoricalMetadataFilteredQuery.isPlaceholderData),
            categoricalError: categoricalMetadataQuery.error?.message,
            comparisonLoading: metadataTagDistributionsQuery.isFetching,
            comparisonError: metadataTagDistributionsQuery.error?.message
        })
    );

    const distributionSources = $derived<DistributionSource[]>(
        buildDistributionSources({
            classSource: classDistributionSource,
            metadataSource: metadataDistributionSource,
            hasAnnotationClasses
        })
    );

    // Selecting a histogram range (bin click or press-drag-release) narrows
    // the metadata filter for that key; re-selecting the current range resets it.
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

<DatasetDistributionPanel
    sources={distributionSources}
    initialCountMode={countMode}
    {onClose}
    onBarClick={onClassBarClick}
    onCountModeChange={(mode) => (countMode = mode)}
    onHistogramRangeSelect={handleHistogramRangeSelect}
    onCategoricalValueToggle={handleCategoricalValueToggle}
    onCategoricalValuesClear={(metadataKey) =>
        updateCategoricalMetadataValues(
            withoutCategoricalValues($categoricalMetadataValues, metadataKey)
        )}
    onCategoricalRetry={() => categoricalMetadataQuery.refetch()}
    {histogramBinCount}
    onHistogramBinCountChange={(binCount) => (histogramBinCount = binCount)}
    comparisonTagItems={distributionSampleTagItems}
    selectedComparisonTagIds={comparisonTagIds}
    onComparisonTagIdsChange={(ids) => (comparisonTagIds = ids)}
    onGroupChange={(sourceId, groupId) => {
        activeDistributionSourceId = sourceId;
        activeDistributionGroupId = groupId;
    }}
/>
