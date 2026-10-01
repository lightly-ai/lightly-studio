<script lang="ts">
    import { buildHistogramOption } from './buildHistogramOption';
    import HistogramChart from './HistogramChart/HistogramChart.svelte';
    import type { HistogramData, HistogramRange, HistogramSeries } from './types';

    type ValueMode = NonNullable<
        NonNullable<Parameters<typeof buildHistogramOption>[2]>['valueMode']
    >;

    interface Props {
        /** Bin edges and per-bin counts (see `HistogramData`). */
        data: HistogramData;
        /** Optional named histograms rendered on the same bin axis. */
        series?: HistogramSeries[];
        /**
         * Selected value range. Bins overlapping it render in the accent
         * color, the rest dimmed. Omit to render all bins in the accent color.
         */
        selectedRange?: HistogramRange;
        /** Chart height in px (default 48 — an inline sparkline above a slider). */
        heightPx?: number;
        /**
         * Renders bin-edge values on the x-axis and counts on the y-axis.
         * Leave off for the inline filter-panel variant, where the slider
         * underneath provides the scale.
         */
        showAxes?: boolean;
        /** Whether bin heights show raw counts or percentages (default 'number'). */
        valueMode?: ValueMode;
        /**
         * Called with the value interval spanned by the user's selection:
         * press on a bin and release on another to select the range across
         * them, or click a single bin to select just its interval. While
         * dragging, the prospective range is previewed via the highlight.
         */
        onRangeSelect?: (range: HistogramRange) => void;
    }

    const {
        data,
        series = [],
        selectedRange,
        heightPx = 48,
        showAxes = false,
        valueMode = 'number',
        onRangeSelect
    }: Props = $props();

    const isEmpty = $derived(data.counts.length === 0 || data.binEdges.length < 2);
</script>

{#if !isEmpty}
    <HistogramChart
        {data}
        {series}
        {selectedRange}
        {heightPx}
        {showAxes}
        {valueMode}
        {onRangeSelect}
    />
{/if}
