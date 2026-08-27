<script lang="ts">
    import type { ECharts } from 'echarts/core';
    import { buildHistogramOption } from './buildHistogramOption';
    import { createHistogramChart } from './createHistogramChart';
    import { createHistogramDragRange } from './createHistogramDragRange.svelte';
    import type { HistogramData, HistogramRange, HistogramSeries } from './types';

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
        onRangeSelect
    }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: ECharts | null = $state(null);

    const isEmpty = $derived(data.counts.length === 0 || data.binEdges.length < 2);

    const drag = createHistogramDragRange({
        getBinEdges: () => data.binEdges,
        getOnRangeSelect: () => onRangeSelect
    });

    $effect(() => {
        if (!container) return;
        const setup = createHistogramChart({
            container,
            getBinCount: () => data.counts.length,
            onDragStart: drag.start,
            onDragMove: drag.move,
            onDragEnd: drag.end
        });
        chart = setup.chart;
        return () => {
            setup.destroy();
            chart = null;
        };
    });

    $effect(() => {
        if (!chart) return;
        // While dragging, preview the prospective selection.
        chart.setOption(
            buildHistogramOption(data, drag.range ?? selectedRange, { showAxes, series }),
            true
        );
    });
</script>

{#if !isEmpty}
    <div
        bind:this={container}
        class="w-full select-none dark:[color-scheme:dark]"
        class:cursor-crosshair={onRangeSelect}
        style="height: {heightPx}px"
        data-testid="histogram"
    ></div>
{/if}
