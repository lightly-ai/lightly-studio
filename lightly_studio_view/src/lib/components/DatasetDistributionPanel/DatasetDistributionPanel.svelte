<script lang="ts">
    import { X } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { BarChart, type CategoryCount } from '$lib/components/BarChart';
    import { Histogram, type HistogramRange } from '$lib/components/Histogram';
    import { formatFloat, formatInteger } from '$lib/utils';
    import DistributionConfigDialog from './DistributionConfigDialog/DistributionConfigDialog.svelte';
    import ExpandDialog from './ExpandDialog/ExpandDialog.svelte';
    import PanelHeader from './PanelHeader/PanelHeader.svelte';
    import { selectVisibleCounts } from './selectVisibleCounts';
    import {
        HISTOGRAM_BIN_COUNT_ITEMS,
        type DistributionConfig,
        type DistributionSource,
        type DistributionSourceGroup
    } from './types';
    import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';

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
        onHistogramBinCountChange
    }: Props = $props();

    // Normalise to a source list so the rest of the panel has one code path.
    const resolvedSources = $derived<DistributionSource[]>(
        sources ?? [{ id: 'class', label: 'Class labels', data: data ?? [] }]
    );
    const hasSourceSelector = $derived(resolvedSources.length > 1);

    let selectedSourceId = $state<string | undefined>(undefined);
    let selectedGroupId = $state<string | undefined>(undefined);

    const groupHasContent = (group: DistributionSourceGroup): boolean =>
        (group.data?.length ?? 0) > 0 || group.histogram != null;

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
    const activeData = $derived<CategoryCount[]>(activeGroup?.data ?? activeSource.data ?? []);
    // A group/source carrying bins renders as a histogram instead of a bar
    // chart; the categorical controls (sort, top-N, orientation) don't apply.
    const activeHistogram = $derived(activeGroup?.histogram ?? activeSource.histogram ?? null);
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
        n: topN,
        sortBy: 'count',
        manualClasses: [],
        orientation: 'horizontal',
        countMode: initialCountMode
    });
    let configDialogOpen = $state(false);
    let expandOpen = $state(false);
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

    const visible = $derived(selectVisibleCounts(activeData, config));
    const totalCount = $derived(activeData.reduce((sum, item) => sum + item.count, 0));

    function applyConfig(next: DistributionConfig) {
        if (next.countMode !== config.countMode) {
            onCountModeChange?.(next.countMode ?? AnnotationCountMode.OBJECTS);
        }
        config = next;
    }
</script>

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
    {#if hasSourceSelector}
        <!-- Fixed-width labels + flex-1 triggers keep both selects the same
             width, filling the panel row. -->
        <div class="mt-2 flex flex-col gap-2" data-testid="dataset-distribution-source">
            <div class="flex items-center gap-2">
                <span class="w-[100px] shrink-0 text-xs text-muted-foreground">Distribution</span>
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
        </div>
    {:else if activeData.length > 0}
        <PanelHeader
            {config}
            classCount={activeData.length}
            visibleClassCount={visible.length}
            totalCount={showTotalCount ? totalCount : undefined}
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
        {:else}
            <BarChart
                data={visible}
                orientation={config.orientation}
                maxHeightPx={chartHeight || undefined}
                maxWidthPx={clientWidth || undefined}
                {totalCount}
                {onBarClick}
            />
        {/if}
    </div>
</div>
<DistributionConfigDialog
    bind:open={configDialogOpen}
    allClasses={activeData.map((item) => item.label)}
    {config}
    onApply={applyConfig}
/>
<ExpandDialog
    bind:open={expandOpen}
    data={activeData}
    {config}
    {valueNoun}
    onConfigChange={applyConfig}
    {onBarClick}
/>
