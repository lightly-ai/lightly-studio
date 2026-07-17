<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { Histogram, type HistogramData, type HistogramRange } from '$lib/components/Histogram';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { formatFloat, formatInteger } from '$lib/utils';
    import { HISTOGRAM_BIN_COUNT_ITEMS } from '../types';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Bin edges and per-bin counts. */
        data: HistogramData;
        /** Label of the charted field (e.g. the metadata key). */
        label: string;
        /** Active filter range; bins outside it render dimmed. */
        selectedRange?: HistogramRange;
        /** Noun for the header summary (e.g. 'samples'). */
        valueNoun?: string;
        /** Currently applied bin count, shared with the panel. */
        binCount: number;
        /** Invoked when the user picks a new bin count. Omit to hide the selector. */
        onBinCountChange?: (binCount: number) => void;
        /** Invoked when the user selects a value range on the chart. */
        onRangeSelect?: (range: HistogramRange) => void;
    }

    let {
        open = $bindable(),
        data,
        label,
        selectedRange,
        valueNoun = 'samples',
        binCount,
        onBinCountChange,
        onRangeSelect
    }: Props = $props();

    // Measured height of the chart viewport; drives the chart's height budget
    // (bind:clientHeight is backed by a ResizeObserver).
    let chartHeight = $state(0);

    const totalCount = $derived(data.counts.reduce((sum, count) => sum + count, 0));

    const binCountItems: SelectItem[] = HISTOGRAM_BIN_COUNT_ITEMS.map((count) => ({
        value: String(count),
        label: `${count} bins`
    }));
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="flex h-[92vh] max-w-[94vw] flex-col sm:max-w-[94vw]">
        <Dialog.Header>
            <Dialog.Title>Distribution · {label}</Dialog.Title>
            <Dialog.Description>
                Click or drag across bars to filter by value range; re-select to reset
            </Dialog.Description>
        </Dialog.Header>
        <div class="flex flex-wrap items-center justify-between gap-2">
            <span
                class="text-xs text-muted-foreground"
                data-testid="dataset-distribution-expanded-histogram-summary"
            >
                {formatInteger(totalCount)}
                {valueNoun} · {data.counts.length}
                {data.counts.length === 1 ? 'bin' : 'bins'} · {formatFloat(
                    data.binEdges[0]
                )}–{formatFloat(data.binEdges[data.binEdges.length - 1])}
            </span>
            {#if onBinCountChange}
                <Select
                    items={binCountItems}
                    value={String(binCount)}
                    size="xs"
                    class="w-28"
                    testId="dataset-distribution-expanded-bin-count"
                    selectProps={{ 'aria-label': 'Histogram bin count' }}
                    onValueChange={(value) => onBinCountChange(Number(value))}
                />
            {/if}
        </div>
        <div class="min-h-0 flex-1 dark:[color-scheme:dark]" bind:clientHeight={chartHeight}>
            <Histogram
                {data}
                {selectedRange}
                heightPx={chartHeight || 480}
                showAxes
                {onRangeSelect}
            />
        </div>
    </Dialog.Content>
</Dialog.Root>
