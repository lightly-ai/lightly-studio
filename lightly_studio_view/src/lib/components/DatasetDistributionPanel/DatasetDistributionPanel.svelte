<script lang="ts">
    import { X } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { BarChart, type CategoryCount, type ChartSeries } from '$lib/components/BarChart';
    import type { MetadataDistributionSeriesResult } from '$lib/hooks/useMetadataDistribution/useMetadataDistributionSeries';
    import DistributionConfigDialog from './DistributionConfigDialog/DistributionConfigDialog.svelte';
    import MetadataDistributionData from './MetadataDistributionData.svelte';
    import ExpandDialog from './ExpandDialog/ExpandDialog.svelte';
    import PanelHeader from './PanelHeader/PanelHeader.svelte';
    import { selectVisibleCounts } from './selectVisibleCounts';
    import type { DistributionConfig, DistributionSource } from './types';

    interface Props {
        /**
         * Counts for the default (class) source. Ignored when `sources` is
         * provided. Ranking and top-N selection are user-configurable.
         */
        data?: CategoryCount[];
        /**
         * Multiple selectable sources (class labels, tags, metadata keys,
         * eval …). When provided, a source selector is shown in the header and
         * `data` is ignored. The same bar-chart UI renders every source.
         */
        sources?: DistributionSource[];
        title?: string;
        /** Top classes shown by default. */
        topN?: number;
        /** Renders a close button in the header when provided. */
        onClose?: () => void;
        /** Called with the clicked class. */
        onBarClick?: (item: CategoryCount) => void;
    }

    const {
        data,
        sources,
        title = 'Class distribution',
        topN = 20,
        onClose,
        onBarClick
    }: Props = $props();

    // Normalise to a source list so the rest of the panel has one code path.
    const resolvedSources = $derived<DistributionSource[]>(
        sources ?? [{ id: 'class', label: 'Class labels', data: data ?? [] }]
    );
    const hasSourceSelector = $derived(resolvedSources.length > 1);

    let selectedSourceId = $state<string | undefined>(undefined);
    let selectedGroupId = $state<string | undefined>(undefined);
    // Tag ids overlaid on the metadata distribution (the current selection is
    // always shown as an implicit series alongside these).
    let compareTagIds = $state<string[]>([]);

    const activeSource = $derived(
        resolvedSources.find((source) => source.id === selectedSourceId) ?? resolvedSources[0]
    );
    const activeGroup = $derived(
        activeSource.groups?.find((group) => group.id === selectedGroupId) ??
            activeSource.groups?.[0]
    );
    const isMetadata = $derived(activeSource.kind === 'metadata');
    const valueNoun = $derived(activeSource.valueNoun ?? 'annotations');

    const sourceItems = $derived<SelectItem[]>(
        resolvedSources.map((source) => ({ value: source.id, label: source.label }))
    );
    const groupItems = $derived<SelectItem[]>(
        (activeSource.groups ?? []).map((group) => ({ value: group.id, label: group.label }))
    );

    // Default to horizontal bars: categories stack down the left gutter and the
    // chart scrolls vertically, avoiding the initial horizontal scroll that
    // vertical bars produce once there are more than a handful of classes.
    // Metadata sources default to percentages so differently-sized tags stay
    // comparable; annotation sources ignore `normalize`.
    let config: DistributionConfig = $state({
        mode: 'topN',
        n: topN,
        sortBy: 'count',
        manualClasses: [],
        orientation: 'horizontal',
        normalize: 'percentage',
        scale: 'linear'
    });
    let configDialogOpen = $state(false);
    let expandOpen = $state(false);

    // --- Annotation-style (pre-fetched) source ---
    const annotationData = $derived<CategoryCount[]>(activeGroup?.data ?? activeSource.data ?? []);
    const annotationVisible = $derived(selectVisibleCounts(annotationData, config));
    const annotationTotal = $derived(annotationData.reduce((sum, item) => sum + item.count, 0));

    // --- Metadata source: fan the distribution endpoint across compared tags ---
    const compareTags = $derived(activeSource.compareTags ?? []);
    const selectedCompareTags = $derived(
        compareTags.filter((tag) => compareTagIds.includes(tag.id))
    );
    const metaSeriesInputs = $derived(
        isMetadata
            ? [
                  { id: 'current', label: 'Current', filter: activeSource.baseFilter ?? null },
                  ...selectedCompareTags.map((tag) => ({
                      id: tag.id,
                      label: tag.label,
                      filter: tag.filter
                  }))
              ]
            : []
    );

    // Populated by the headless <MetadataDistributionData> (mounted only for
    // metadata sources, so `createQueries` never runs for annotation panels).
    let metaResult = $state<MetadataDistributionSeriesResult>({
        series: [],
        chartMode: undefined,
        isLoading: false,
        isError: false
    });

    const metaPrimary = $derived<CategoryCount[]>(metaResult.series[0]?.data ?? []);
    const metaTotal = $derived(metaPrimary.reduce((sum, item) => sum + item.count, 0));
    // Counts summed across series, used to rank categories for top-N/sort so a
    // value carried only by an overlaid tag can still make the cut.
    const metaAggregate = $derived.by<CategoryCount[]>(() => {
        const totals = new Map<string, number>();
        for (const series of metaResult.series) {
            for (const item of series.data) {
                totals.set(item.label, (totals.get(item.label) ?? 0) + item.count);
            }
        }
        return [...totals].map(([label, count]) => ({ label, count }));
    });
    // Ordered labels the chart shows: histograms keep their natural bin order;
    // categorical keys apply the panel's sort + top-N.
    const metaOrderedLabels = $derived.by<string[]>(() => {
        if (metaResult.chartMode === 'histogram') return metaPrimary.map((item) => item.label);
        return selectVisibleCounts(metaAggregate, config).map((item) => item.label);
    });
    const metaVisibleSeries = $derived<ChartSeries[]>(
        metaResult.series.map((series) => {
            const byLabel = new Map(series.data.map((item) => [item.label, item.count]));
            return {
                ...series,
                data: metaOrderedLabels.map((label) => ({
                    label,
                    count: byLabel.get(label) ?? 0
                }))
            };
        })
    );

    // Unified header inputs, chosen per source flavour.
    const classCount = $derived(isMetadata ? metaAggregate.length : annotationData.length);
    const visibleClassCount = $derived(
        isMetadata ? metaOrderedLabels.length : annotationVisible.length
    );
    const totalCount = $derived(isMetadata ? metaTotal : annotationTotal);
    const hasChart = $derived(
        isMetadata ? metaResult.series.length > 0 : annotationData.length > 0
    );
    const allClasses = $derived(
        isMetadata
            ? metaAggregate.map((item) => item.label)
            : annotationData.map((item) => item.label)
    );

    const toggleCompareTag = (tagId: string) => {
        compareTagIds = compareTagIds.includes(tagId)
            ? compareTagIds.filter((id) => id !== tagId)
            : [...compareTagIds, tagId];
    };
</script>

{#if isMetadata}
    <MetadataDistributionData
        collectionId={activeSource.collectionId ?? ''}
        metadataKey={activeGroup?.id}
        series={metaSeriesInputs}
        endpoint={activeSource.distributionEndpoint ?? 'metadata'}
        bind:result={metaResult}
    />
{/if}
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
                ariaLabel="Close class distribution panel"
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
        <div
            class="mt-2 flex flex-wrap items-center gap-2"
            data-testid="dataset-distribution-source"
        >
            <span class="text-xs text-muted-foreground">Source</span>
            <Select
                items={sourceItems}
                value={activeSource.id}
                size="xs"
                class="w-40"
                testId="dataset-distribution-source-select"
                onValueChange={(value) => {
                    selectedSourceId = value;
                    selectedGroupId = undefined;
                }}
            />
            {#if groupItems.length > 0}
                <span class="text-xs text-muted-foreground"
                    >{activeSource.groupLabel ?? 'Field'}</span
                >
                <Select
                    items={groupItems}
                    value={activeGroup?.id}
                    size="xs"
                    class="w-48"
                    testId="dataset-distribution-group-select"
                    onValueChange={(value) => (selectedGroupId = value)}
                />
            {/if}
        </div>
    {/if}
    {#if isMetadata && compareTags.length > 0}
        <div
            class="mt-2 flex flex-wrap items-center gap-1.5"
            data-testid="dataset-distribution-compare-tags"
        >
            <span class="text-xs text-muted-foreground">Compare tags</span>
            {#each compareTags as tag (tag.id)}
                {@const selected = compareTagIds.includes(tag.id)}
                <button
                    type="button"
                    class="rounded-full border px-2 py-0.5 text-xs transition-colors {selected
                        ? 'border-primary bg-primary/15 text-primary'
                        : 'border-border text-muted-foreground hover:border-primary/60'}"
                    aria-pressed={selected}
                    onclick={() => toggleCompareTag(tag.id)}
                    data-testid={`dataset-distribution-compare-tag-${tag.id}`}
                >
                    {tag.label}
                </button>
            {/each}
        </div>
    {/if}
    {#if hasChart}
        <PanelHeader
            {config}
            {classCount}
            {visibleClassCount}
            {totalCount}
            {valueNoun}
            onConfigure={() => (configDialogOpen = true)}
            onShowAll={() => (config = { ...config, mode: 'topN', n: classCount })}
            onToggleOrientation={() =>
                (config = {
                    ...config,
                    orientation: config.orientation === 'horizontal' ? 'vertical' : 'horizontal'
                })}
            onToggleNormalize={isMetadata
                ? () =>
                      (config = {
                          ...config,
                          normalize: config.normalize === 'percentage' ? 'count' : 'percentage'
                      })
                : undefined}
            onToggleScale={() =>
                (config = {
                    ...config,
                    scale: config.scale === 'log' ? 'linear' : 'log'
                })}
            onExpand={() => (expandOpen = true)}
        />
    {/if}
    <div class="min-h-0 flex-1 overflow-y-auto dark:[color-scheme:dark]">
        {#if isMetadata}
            {#if metaResult.isError}
                <div
                    class="p-8 text-center text-sm text-muted-foreground"
                    data-testid="dataset-distribution-error"
                >
                    Failed to load the metadata distribution.
                </div>
            {:else if metaResult.series.length === 0 && metaResult.isLoading}
                <div
                    class="p-8 text-center text-sm text-muted-foreground"
                    data-testid="dataset-distribution-loading"
                >
                    Loading…
                </div>
            {:else}
                <BarChart
                    series={metaVisibleSeries}
                    mode={metaResult.chartMode ?? 'bar'}
                    normalize={config.normalize}
                    scale={config.scale}
                    orientation={config.orientation}
                />
            {/if}
        {:else}
            <BarChart
                data={annotationVisible}
                scale={config.scale}
                orientation={config.orientation}
                totalCount={annotationTotal}
                {onBarClick}
            />
        {/if}
    </div>
</div>
<DistributionConfigDialog
    bind:open={configDialogOpen}
    {allClasses}
    {config}
    onApply={(next) => (config = next)}
/>
<ExpandDialog
    bind:open={expandOpen}
    data={annotationData}
    series={isMetadata ? metaVisibleSeries : undefined}
    mode={metaResult.chartMode ?? 'bar'}
    normalize={config.normalize}
    {classCount}
    {visibleClassCount}
    {totalCount}
    {allClasses}
    {config}
    {valueNoun}
    onConfigChange={(next) => (config = next)}
    onToggleNormalize={isMetadata
        ? () =>
              (config = {
                  ...config,
                  normalize: config.normalize === 'percentage' ? 'count' : 'percentage'
              })
        : undefined}
    onBarClick={isMetadata ? undefined : onBarClick}
/>
