<script lang="ts">
    import type { ECharts } from 'echarts/core';
    import { buildHistogramOption } from './buildHistogramOption';
    import { createHistogramChart } from './createHistogramChart';
    import type { HistogramData, HistogramRange } from './types';

    interface Props {
        /** Bin edges and per-bin counts (see `HistogramData`). */
        data: HistogramData;
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

    const { data, selectedRange, heightPx = 48, showAxes = false, onRangeSelect }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: ECharts | null = $state(null);

    const isEmpty = $derived(data.counts.length === 0 || data.binEdges.length < 2);

    // Drag selection state: bin indices under the press and the current pointer.
    let dragStartIndex = $state<number | null>(null);
    let dragCurrentIndex = $state<number | null>(null);

    const dragRange = $derived.by<HistogramRange | undefined>(() => {
        if (dragStartIndex === null || dragCurrentIndex === null) return undefined;
        const lower = Math.min(dragStartIndex, dragCurrentIndex);
        const upper = Math.max(dragStartIndex, dragCurrentIndex);
        return { min: data.binEdges[lower], max: data.binEdges[upper + 1] };
    });

    $effect(() => {
        if (!container) return;
        const setup = createHistogramChart({
            container,
            getBinCount: () => data.counts.length,
            onDragStart: (binIndex) => {
                if (!onRangeSelect) return;
                dragStartIndex = binIndex;
                dragCurrentIndex = binIndex;
            },
            onDragMove: (binIndex) => {
                if (dragStartIndex === null) return;
                dragCurrentIndex = binIndex;
            },
            onDragEnd: () => {
                const range = dragRange;
                dragStartIndex = null;
                dragCurrentIndex = null;
                if (range) onRangeSelect?.(range);
            }
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
        chart.setOption(buildHistogramOption(data, dragRange ?? selectedRange, { showAxes }), true);
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
