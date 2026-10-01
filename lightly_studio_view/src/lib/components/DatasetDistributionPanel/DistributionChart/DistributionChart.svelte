<script lang="ts">
    import { BarChart, type CategoryCount } from '$lib/components/BarChart';
    import { Histogram, type HistogramRange } from '$lib/components/Histogram';
    import { Button } from '$lib/components';
    import type { DistributionConfig, DistributionSourceGroup } from '../types';

    type Categorical = NonNullable<DistributionSourceGroup['categorical']>;

    interface Props {
        activeHistogram: NonNullable<DistributionSourceGroup['histogram']> | null;
        activeCategorical: Categorical | null;
        viewConfig: DistributionConfig;
        visible: CategoryCount[];
        totalCount: number;
        selectedRange: HistogramRange | undefined;
        onHistogramRangeSelect?: (range: HistogramRange) => void;
        onBarClick?: (item: CategoryCount) => void;
        onCategoricalRetry?: () => void;
    }

    const {
        activeHistogram,
        activeCategorical,
        viewConfig,
        visible,
        totalCount,
        selectedRange,
        onHistogramRangeSelect,
        onBarClick,
        onCategoricalRetry
    }: Props = $props();

    let chartHeight = $state(0);
    let clientWidth = $state(0);
</script>

{#snippet categoricalEmptyState()}
    <span>No matching samples for this metadata field.</span>
{/snippet}

<div
    class="min-h-0 flex-1 overflow-y-auto dark:[color-scheme:dark]"
    bind:clientHeight={chartHeight}
    bind:clientWidth
>
    {#if activeHistogram}
        <Histogram
            data={activeHistogram}
            {selectedRange}
            heightPx={chartHeight || 240}
            showAxes
            onRangeSelect={onHistogramRangeSelect}
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
            orientation={viewConfig.orientation}
            maxHeightPx={chartHeight || undefined}
            maxWidthPx={clientWidth || undefined}
            {totalCount}
            {onBarClick}
            emptyState={activeCategorical ? categoricalEmptyState : undefined}
            gridTopPx={4}
        />
    {/if}
</div>
