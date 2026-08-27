<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import {
        Histogram,
        type HistogramData,
        type HistogramRange,
        type HistogramSeries
    } from '$lib/components/Histogram';
    import type { ValueMode } from '../PanelHeader/ValueModeSelect';
    import HistogramExpandToolbar from './HistogramExpandToolbar/HistogramExpandToolbar.svelte';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Bin edges and per-bin counts. */
        data: HistogramData;
        /** Optional comparison histograms sharing the same bin edges. */
        series?: HistogramSeries[];
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
        /** Whether bin heights show raw counts or percentages. */
        valueMode?: ValueMode;
        /** Keeps the expanded and regular histogram views in sync. */
        onValueModeChange?: (mode: ValueMode) => void;
        /** Invoked when the user selects a value range on the chart. */
        onRangeSelect?: (range: HistogramRange) => void;
    }

    let {
        open = $bindable(),
        data,
        series = [],
        label,
        selectedRange,
        valueNoun = 'samples',
        binCount,
        onBinCountChange,
        valueMode = 'number',
        onValueModeChange,
        onRangeSelect
    }: Props = $props();

    // Measured height of the chart viewport; drives the chart's height budget
    // (bind:clientHeight is backed by a ResizeObserver).
    let chartHeight = $state(0);
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="flex h-[92vh] max-w-[94vw] flex-col sm:max-w-[94vw]">
        <Dialog.Header>
            <Dialog.Title>Distribution · {label}</Dialog.Title>
            <Dialog.Description>
                Click or drag across bars to filter by value range; re-select to reset
            </Dialog.Description>
        </Dialog.Header>
        <HistogramExpandToolbar
            {data}
            {valueNoun}
            {binCount}
            {onBinCountChange}
            {valueMode}
            {onValueModeChange}
        />
        <div class="min-h-0 flex-1 dark:[color-scheme:dark]" bind:clientHeight={chartHeight}>
            <Histogram
                {data}
                {series}
                {selectedRange}
                heightPx={chartHeight || 480}
                showAxes
                {valueMode}
                {onRangeSelect}
            />
        </div>
    </Dialog.Content>
</Dialog.Root>
