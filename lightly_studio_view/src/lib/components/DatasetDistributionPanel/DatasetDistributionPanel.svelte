<script lang="ts">
    import { untrack } from 'svelte';
    import { Maximize2 as Maximize2Icon, X } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { Select, type SelectItem } from '$lib/components/Select';
    import {
        BarChart,
        type CategoryCount,
        type CategoryCountSeries
    } from '$lib/components/BarChart';
    import { Histogram, type HistogramRange } from '$lib/components/Histogram';
    import { formatFloat, formatInteger } from '$lib/utils';
    import DistributionConfigDialog from './DistributionConfigDialog/DistributionConfigDialog.svelte';
    import ExpandDialog from './ExpandDialog/ExpandDialog.svelte';
    import HistogramExpandDialog from './HistogramExpandDialog/HistogramExpandDialog.svelte';
    import PanelHeader from './PanelHeader/PanelHeader.svelte';
    import TagComparisonSelect from './TagComparisonSelect.svelte';
    import { selectVisibleCounts } from './selectVisibleCounts';
    import {
        CATEGORICAL_DISTRIBUTION_SORT_LABELS,
        HISTOGRAM_BIN_COUNT_ITEMS,
        type DistributionConfig,
        type DistributionSource,
        type DistributionSourceGroup
    } from './types';
    import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
    import { MetadataCategoricalFilter } from './MetadataCategoricalFilter';
    import type { CategoricalMetadataValue } from '$lib/services/types';

    interface Props {
        /**
         * Counts for the default (class) source. Ignored when `sources` is
         * provided. Ranking and top-N selection are user-configurable.
         */
        data?: CategoryCount[];
        /**
         * Multiple selectable sources (class labels, tags, metadata keys,
         * eval …). When provided, a source selector is shown in the header and
         * `data` is ignored. Sources with a `histogram` field render as a
         * histogram instead of a bar chart.
         */
        sources?: DistributionSource[];
        title?: string;
        /** Top classes shown by default. */
        topN?: number;
        /** Renders a close button in the header when provided. */
        onClose?: () => void;
        /** Called with the clicked class. */
        onBarClick?: (item: CategoryCount) => void;
        /**
         * Called when the user switches the count mode via the config dialog.
         */
        onCountModeChange?: (mode: AnnotationCountMode) => void;
        /**
         * Initial count mode to use when the panel first mounts. Lets the
         * parent preserve the mode across close/reopen cycles.
         */
        initialCountMode?: AnnotationCountMode;
        /**
         * Called when a histogram range is selected (single-bin click or
         * press-drag-release across bins), with the group id (e.g. the
         * metadata key) and the spanned value interval — lets the host narrow
         * the matching filter to that range.
         */
        onHistogramRangeSelect?: (groupId: string, range: HistogramRange) => void;
        /** Applied histogram bin count, controlled by the host (server default: 20). */
        histogramBinCount?: number;
        /** Called when the user picks a new histogram bin count. */
        onHistogramBinCountChange?: (binCount: number) => void;
        /** Called when a concrete categorical value or Missing is toggled. */
        onCategoricalValueToggle?: (groupId: string, value: CategoricalMetadataValue) => void;
        /** Removes every categorical value selected for the given group. */
        onCategoricalValuesClear?: (groupId: string) => void;
        /** Retries a failed categorical distribution request. */
        onCategoricalRetry?: () => void;
        /** Sample tags available for an independent class-distribution comparison. */
        comparisonTagItems?: SelectItem[];
        /** IDs of the sample tags currently included in the comparison. */
        selectedComparisonTagIds?: string[];
        /** Updates the independent comparison selection without changing the grid filter. */
        onComparisonTagIdsChange?: (ids: string[]) => void;
    }

    const {
        data,
        sources,
        title = 'Distribution',
        topN = 20,
        onClose,
        onBarClick,
        onCountModeChange,
        initialCountMode = AnnotationCountMode.OBJECTS,
        onHistogramRangeSelect,
        histogramBinCount = 20,
        onHistogramBinCountChange,
        onCategoricalValueToggle,
        onCategoricalValuesClear,
        onCategoricalRetry,
        comparisonTagItems = [],
        selectedComparisonTagIds = [],
        onComparisonTagIdsChange
    }: Props = $props();

    // Normalise to a source list so the rest of the panel has one code path.
    const resolvedSources = $derived<DistributionSource[]>(
        sources ?? [{ id: 'class', label: 'Annotation classes', data: data ?? [] }]
    );
    const hasSourceSelector = $derived(resolvedSources.length > 1);

    let selectedSourceId = $state<string | undefined>(undefined);
    let selectedGroupId = $state<string | undefined>(undefined);

    const groupHasContent = (group: DistributionSourceGroup): boolean =>
        (group.data?.length ?? 0) > 0 || group.histogram != null || group.categorical != null;

    const sourceHasContent = (source: DistributionSource): boolean =>
        (source.data?.length ?? 0) > 0 ||
        source.histogram != null ||
        (source.groups?.some(groupHasContent) ?? false);

    // With nothing explicitly selected, land on the first source that actually
    // has something to show. Otherwise an empty leading source (e.g. "All types"
    // before any labeling) would render as empty while a populated source like
    // metadata sits one click away.
    const defaultSource = $derived(resolvedSources.find(sourceHasContent) ?? resolvedSources[0]);
    const activeSource = $derived(
        resolvedSources.find((source) => source.id === selectedSourceId) ?? defaultSource
    );
    const activeGroup = $derived(
        activeSource.groups?.find((group) => group.id === selectedGroupId) ??
            activeSource.groups?.find(groupHasContent) ??
            activeSource.groups?.[0]
    );
    const activeSingleSeriesData = $derived<CategoryCount[]>(
        activeGroup?.data ?? activeSource.data ?? []
    );
    const activeComparisonData = $derived(
        activeGroup?.comparisonData ?? activeSource.comparisonData ?? []
    );
    const activeSeries = $derived<CategoryCountSeries[]>(
        activeComparisonData.map((tag) => ({
            id: tag.sample_tag_id,
            label: tag.sample_tag_name,
            data: tag.counts.map((item) => ({ label: item.label_name, count: item.count }))
        }))
    );
    // Rank the shared axis by the aggregate across tags; individual series stay independent.
    const activeData = $derived.by<CategoryCount[]>(() => {
        if (activeSeries.length === 0) return activeSingleSeriesData;
        const totals = new Map<string, number>();
        for (const series of activeSeries) {
            for (const item of series.data) {
                totals.set(item.label, (totals.get(item.label) ?? 0) + item.count);
            }
        }
        return [...totals].map(([label, count]) => ({ label, count }));
    });
    // A group/source carrying bins renders as a histogram instead of a bar
    // chart; the categorical controls (sort, top-N, orientation) don't apply.
    const activeHistogram = $derived(activeGroup?.histogram ?? activeSource.histogram ?? null);
    const activeCategorical = $derived(activeGroup?.categorical ?? null);
    const categoricalData = $derived<CategoryCount[]>(
        (activeCategorical?.buckets ?? []).map((bucket) => {
            // When filteredBuckets is defined (query has returned) look up the
            // filtered count for this bucket. Absent = 0 (filter removed it entirely).
            const filteredBucket = activeCategorical?.filteredBuckets?.find(
                (fb) => fb.id === bucket.id
            );
            const filteredCount =
                activeCategorical?.filteredBuckets !== undefined
                    ? (filteredBucket?.count ?? 0)
                    : undefined;
            return {
                id: bucket.id,
                label: bucket.label,
                count: bucket.count,
                filteredCount,
                selectable: bucket.kind !== 'other',
                pinned: bucket.kind !== 'value',
                selected:
                    bucket.kind !== 'other' &&
                    activeCategorical?.selectedValues.some((value) =>
                        Object.is(value, bucket.value)
                    )
            };
        })
    );
    const displayedData = $derived(activeCategorical ? categoricalData : activeData);
    const configurationItems = $derived(
        displayedData.map((item) => ({ value: item.id ?? item.label, label: item.label }))
    );
    const activeHistogramRange = $derived(activeGroup?.selectedRange ?? activeSource.selectedRange);
    const handleHistogramRangeSelect = (range: HistogramRange) => {
        const groupId = activeGroup?.id ?? activeSource.id;
        onHistogramRangeSelect?.(groupId, range);
    };
    const histogramTotal = $derived(
        activeHistogram ? activeHistogram.counts.reduce((sum, count) => sum + count, 0) : 0
    );
    const valueNoun = $derived(activeSource.valueNoun ?? 'annotations');

    // Default to horizontal bars: categories stack down the left gutter and the
    // chart scrolls vertically, avoiding the initial horizontal scroll that
    // vertical bars produce once there are more than a handful of classes.
    let config: DistributionConfig = $state({
        mode: 'topN',
        n: untrack(() => topN),
        sortBy: 'count',
        manualClasses: [],
        orientation: 'horizontal',
        countMode: untrack(() => initialCountMode)
    });
    const defaultCategoricalConfig: DistributionConfig = {
        mode: 'topN',
        n: 1,
        sortBy: 'count',
        manualClasses: [],
        orientation: 'horizontal',
        countMode: AnnotationCountMode.SAMPLES
    };
    let categoricalConfigs = $state<Record<string, DistributionConfig>>({});
    const categoricalConfig = $derived<DistributionConfig>(
        activeGroup
            ? (categoricalConfigs[activeGroup.id] ?? {
                  ...defaultCategoricalConfig,
                  n: Math.max(categoricalData.length, 1)
              })
            : defaultCategoricalConfig
    );
    let configDialogOpen = $state(false);
    let expandOpen = $state(false);
    let histogramExpandOpen = $state(false);

    const binCountItems: SelectItem[] = HISTOGRAM_BIN_COUNT_ITEMS.map((count) => ({
        value: String(count),
        label: `${count} bins`
    }));
    // Measured height of the chart viewport; drives the chart's height budget and
    // tracks container resizes (bind:clientHeight is backed by a ResizeObserver).
    let chartHeight = $state(0);
    let clientWidth = $state(0);

    const activeCountMode = $derived(config.countMode ?? AnnotationCountMode.OBJECTS);
    const showTotalCount = $derived(activeCountMode !== AnnotationCountMode.SAMPLES);

    const sourceItems = $derived<SelectItem[]>(
        resolvedSources.map((source) => ({ value: source.id, label: source.label }))
    );
    const groupItems = $derived<SelectItem[]>(
        (activeSource.groups ?? []).map((group) => ({ value: group.id, label: group.label }))
    );

    const activeViewConfig = $derived<DistributionConfig>(
        activeCategorical ? categoricalConfig : config
    );
    const visible = $derived(selectVisibleCounts(displayedData, activeViewConfig));
    const visibleLabels = $derived(new Set(visible.map((item) => item.label)));
    const visibleSeries = $derived(
        activeSeries.map((series) => ({
            ...series,
            data: series.data.filter((item) => visibleLabels.has(item.label))
        }))
    );
    const totalCount = $derived(displayedData.reduce((sum, item) => sum + item.count, 0));

    const handleCategoricalBarClick = (item: CategoryCount) => {
        const bucket = activeCategorical?.buckets.find((candidate) => candidate.id === item.id);
        if (!bucket || bucket.kind === 'other' || !activeGroup) return;
        onCategoricalValueToggle?.(activeGroup.id, bucket.value);
    };

    const setCategoricalConfig = (next: DistributionConfig) => {
        if (!activeGroup) return;
        categoricalConfigs = {
            ...categoricalConfigs,
            [activeGroup.id]: {
                ...next,
                countMode: AnnotationCountMode.SAMPLES
            }
        };
    };

    function applyConfig(next: DistributionConfig) {
        if (activeCategorical) {
            setCategoricalConfig(next);
            return;
        }
        if (next.countMode !== config.countMode) {
            onCountModeChange?.(next.countMode ?? AnnotationCountMode.OBJECTS);
        }
        config = next;
    }
</script>

{#snippet categoricalEmptyState()}
    <span>No matching samples for this metadata field.</span>
{/snippet}

<div
    class="flex h-full min-w-0 flex-1 flex-col rounded-[1vw] bg-card p-4"
    data-testid="dataset-distribution-panel"
>
    <div class="flex items-center justify-between">
        <Typography variant="h5" component="h2" className="text-foreground">
            {title}
        </Typography>
        {#if onClose}
            <Button
                variant="ghost"
                icon={X}
                ariaLabel="Close distribution panel"
                buttonProps={{
                    size: 'sm',
                    class: 'h-8 w-8 p-0',
                    onclick: onClose,
                    'data-testid': 'dataset-distribution-close-button'
                }}
            />
        {/if}
    </div>
    {#if hasSourceSelector || groupItems.length > 0}
        <!-- Fixed-width labels + flex-1 triggers keep both selects the same
             width, filling the panel row. -->
        <div class="mt-2 flex flex-col gap-2" data-testid="dataset-distribution-source">
            {#if hasSourceSelector}
                <div class="flex items-center gap-2">
                    <span class="w-[100px] shrink-0 text-xs text-muted-foreground"
                        >Distribution</span
                    >
                    <Select
                        items={sourceItems}
                        value={activeSource.id}
                        size="xs"
                        class="min-w-0 flex-1"
                        testId="dataset-distribution-source-select"
                        onValueChange={(value) => {
                            selectedSourceId = value;
                            selectedGroupId = undefined;
                        }}
                    />
                </div>
            {/if}

            {#if groupItems.length > 0}
                <div class="flex items-center gap-2">
                    <span class="w-[100px] shrink-0 text-xs text-muted-foreground"
                        >{activeSource.groupLabel ?? 'Field'}</span
                    >
                    <Select
                        items={groupItems}
                        value={activeGroup?.id}
                        size="xs"
                        class="min-w-0 flex-1"
                        testId="dataset-distribution-group-select"
                        onValueChange={(value) => (selectedGroupId = value)}
                    />
                </div>
            {/if}
        </div>
    {/if}
    {#if activeSource.id === 'classes' && comparisonTagItems.length > 0 && onComparisonTagIdsChange}
        <div class="mt-2 flex items-center gap-2">
            <span class="w-[100px] shrink-0 text-xs text-muted-foreground">Compare by</span>
            <TagComparisonSelect
                items={comparisonTagItems}
                selectedIds={selectedComparisonTagIds}
                onChange={onComparisonTagIdsChange}
            />
        </div>
    {/if}
    {#if activeHistogram}
        <div class="mt-2 flex flex-wrap items-center justify-between gap-2">
            <span
                class="text-xs text-muted-foreground"
                data-testid="dataset-distribution-histogram-summary"
            >
                {formatInteger(histogramTotal)}
                {valueNoun} · {activeHistogram.counts.length}
                {activeHistogram.counts.length === 1 ? 'bin' : 'bins'} · {formatFloat(
                    activeHistogram.binEdges[0]
                )}–{formatFloat(activeHistogram.binEdges[activeHistogram.binEdges.length - 1])}
            </span>
            <div class="flex items-center gap-1">
                {#if onHistogramBinCountChange}
                    <Select
                        items={binCountItems}
                        value={String(histogramBinCount)}
                        size="xs"
                        class="w-24"
                        testId="dataset-distribution-bin-count"
                        selectProps={{ 'aria-label': 'Histogram bin count' }}
                        onValueChange={(value) => onHistogramBinCountChange(Number(value))}
                    />
                {/if}
                <Button
                    variant="ghost"
                    icon={Maximize2Icon}
                    ariaLabel="Expand distribution"
                    buttonProps={{
                        size: 'sm',
                        class: 'h-8 w-8 p-0',
                        onclick: () => (histogramExpandOpen = true),
                        'data-testid': 'dataset-distribution-histogram-expand'
                    }}
                />
            </div>
        </div>
    {:else if activeCategorical && activeGroup}
        <MetadataCategoricalFilter
            buckets={activeCategorical.buckets}
            selectedValues={activeCategorical.selectedValues}
            loading={activeCategorical.loading}
            onToggle={(value) => onCategoricalValueToggle?.(activeGroup.id, value)}
            onClear={() => onCategoricalValuesClear?.(activeGroup.id)}
        />
        {#if activeCategorical.loading && activeCategorical.buckets.length > 0}
            <p class="mt-1 text-xs text-muted-foreground" role="status">Updating values…</p>
        {/if}
        {#if activeCategorical.error && activeCategorical.buckets.length > 0}
            <div
                class="mt-1 flex items-center justify-between gap-2 text-xs text-destructive"
                role="alert"
            >
                <span>Could not update metadata distribution.</span>
                {#if onCategoricalRetry}
                    <button
                        class="underline max-sm:min-h-11"
                        type="button"
                        onclick={onCategoricalRetry}
                    >
                        Retry
                    </button>
                {/if}
            </div>
        {/if}
        {#if categoricalData.length > 0}
            <div class="mt-2">
                <PanelHeader
                    config={categoricalConfig}
                    classCount={categoricalData.length}
                    visibleClassCount={visible.length}
                    {totalCount}
                    {valueNoun}
                    categoryNoun="value"
                    categoryNounPlural="values"
                    sortLabels={CATEGORICAL_DISTRIBUTION_SORT_LABELS}
                    onConfigure={() => (configDialogOpen = true)}
                    onShowAll={() =>
                        setCategoricalConfig({
                            ...categoricalConfig,
                            mode: 'topN',
                            n: categoricalData.length
                        })}
                    onToggleOrientation={() =>
                        setCategoricalConfig({
                            ...categoricalConfig,
                            orientation:
                                categoricalConfig.orientation === 'horizontal'
                                    ? 'vertical'
                                    : 'horizontal'
                        })}
                    onExpand={() => (expandOpen = true)}
                />
            </div>
        {/if}
    {:else if activeData.length > 0}
        <div class="mt-2">
            <PanelHeader
                {config}
                classCount={activeData.length}
                visibleClassCount={visible.length}
                totalCount={showTotalCount && activeSeries.length === 0 ? totalCount : undefined}
                seriesCount={activeSeries.length || undefined}
                {valueNoun}
                onConfigure={() => (configDialogOpen = true)}
                onShowAll={() => (config = { ...config, mode: 'topN', n: activeData.length })}
                onToggleOrientation={() =>
                    (config = {
                        ...config,
                        orientation: config.orientation === 'horizontal' ? 'vertical' : 'horizontal'
                    })}
                onExpand={() => (expandOpen = true)}
            />
        </div>
    {/if}
    <div
        class="min-h-0 flex-1 overflow-y-auto dark:[color-scheme:dark]"
        bind:clientHeight={chartHeight}
        bind:clientWidth
    >
        {#if activeHistogram}
            <Histogram
                data={activeHistogram}
                selectedRange={activeHistogramRange}
                heightPx={chartHeight || 240}
                showAxes
                onRangeSelect={onHistogramRangeSelect ? handleHistogramRangeSelect : undefined}
            />
        {:else if activeCategorical?.loading && activeCategorical.buckets.length === 0}
            <div class="p-8 text-center text-sm text-muted-foreground" role="status">
                Loading metadata distribution…
            </div>
        {:else if activeCategorical?.error && activeCategorical.buckets.length === 0}
            <div class="space-y-2 p-8 text-center text-sm" role="alert">
                <p class="text-destructive">Could not load metadata distribution.</p>
                {#if onCategoricalRetry}
                    <Button
                        variant="secondary"
                        buttonProps={{
                            size: 'sm',
                            class: 'max-sm:min-h-11',
                            onclick: onCategoricalRetry,
                            'data-testid': 'metadata-categorical-retry'
                        }}>Retry</Button
                    >
                {/if}
            </div>
        {:else}
            {#if activeCategorical}
                <ul class="sr-only" aria-label="Categorical metadata value counts">
                    {#each activeCategorical.buckets as bucket (bucket.id)}
                        <li>
                            {bucket.label}: {bucket.count} samples{bucket.kind === 'other'
                                ? ', aggregated and not selectable'
                                : activeCategorical.selectedValues.some((value) =>
                                        Object.is(value, bucket.value)
                                    )
                                  ? ', selected'
                                  : ''}
                        </li>
                    {/each}
                </ul>
            {/if}
            <BarChart
                data={visible}
                orientation={activeViewConfig.orientation}
                maxHeightPx={chartHeight || undefined}
                maxWidthPx={clientWidth || undefined}
                {totalCount}
                series={activeCategorical ? [] : visibleSeries}
                onBarClick={activeCategorical ? handleCategoricalBarClick : onBarClick}
                emptyState={activeCategorical ? categoricalEmptyState : undefined}
                gridTopPx={4}
            />
        {/if}
    </div>
</div>
{#if !activeHistogram}
    <DistributionConfigDialog
        bind:open={configDialogOpen}
        allClasses={displayedData.map((item) => item.label)}
        items={configurationItems}
        config={activeViewConfig}
        showCountMode={!activeCategorical}
        itemNoun={activeCategorical ? 'value' : 'class'}
        itemNounPlural={activeCategorical ? 'values' : 'classes'}
        sortLabels={activeCategorical ? CATEGORICAL_DISTRIBUTION_SORT_LABELS : undefined}
        onApply={applyConfig}
    />
    <ExpandDialog
        bind:open={expandOpen}
        data={displayedData}
        series={activeCategorical ? [] : activeSeries}
        config={activeViewConfig}
        {valueNoun}
        categoryNoun={activeCategorical ? 'value' : 'class'}
        categoryNounPlural={activeCategorical ? 'values' : 'classes'}
        sortLabels={activeCategorical ? CATEGORICAL_DISTRIBUTION_SORT_LABELS : undefined}
        showCountMode={!activeCategorical}
        onConfigChange={applyConfig}
        onBarClick={activeCategorical ? handleCategoricalBarClick : onBarClick}
    />
{/if}
{#if activeHistogram}
    <HistogramExpandDialog
        bind:open={histogramExpandOpen}
        data={activeHistogram}
        label={activeGroup?.label ?? activeSource.label}
        selectedRange={activeHistogramRange}
        {valueNoun}
        binCount={histogramBinCount}
        onBinCountChange={onHistogramBinCountChange}
        onRangeSelect={onHistogramRangeSelect ? handleHistogramRangeSelect : undefined}
    />
{/if}
