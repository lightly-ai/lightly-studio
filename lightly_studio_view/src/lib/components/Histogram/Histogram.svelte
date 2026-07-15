<script lang="ts">
    import { onDestroy } from 'svelte';
    import * as echarts from 'echarts/core';
    import { CustomChart } from 'echarts/charts';
    import { GridComponent, TooltipComponent } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';
    import { buildHistogramOption } from './buildHistogramOption';
    import type { HistogramData, HistogramRange } from './types';

    echarts.use([CustomChart, GridComponent, TooltipComponent, CanvasRenderer]);

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
    let chart: echarts.ECharts | null = $state(null);

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

    /** Maps a canvas x-offset to the bin index under it (clamped to the domain). */
    const pixelToBinIndex = (instance: echarts.ECharts, offsetX: number): number => {
        // The x-axis is a value axis over bin indices, so the converted
        // coordinate is a fractional bin index.
        const index = Math.floor(instance.convertFromPixel({ xAxisIndex: 0 }, offsetX));
        return Math.min(Math.max(index, 0), data.counts.length - 1);
    };

    $effect(() => {
        if (!container) return;
        const instance = echarts.init(container, null, { renderer: 'canvas' });
        chart = instance;

        // Range selection: press (zrender events fire anywhere on the canvas,
        // not just on bars) → drag → release. The window listener catches
        // releases outside the canvas.
        const zr = instance.getZr();
        const handleMouseDown = (event: { offsetX: number }) => {
            if (!onRangeSelect) return;
            dragStartIndex = pixelToBinIndex(instance, event.offsetX);
            dragCurrentIndex = dragStartIndex;
        };
        const handleMouseMove = (event: { offsetX: number }) => {
            if (dragStartIndex === null) return;
            dragCurrentIndex = pixelToBinIndex(instance, event.offsetX);
        };
        const handleWindowMouseMove = (event: MouseEvent) => {
            if (dragStartIndex === null) return;
            const offsetX = event.clientX - container.getBoundingClientRect().left;
            dragCurrentIndex = pixelToBinIndex(instance, offsetX);
        };
        const handleWindowMouseUp = () => {
            const range = dragRange;
            dragStartIndex = null;
            dragCurrentIndex = null;
            if (range) onRangeSelect?.(range);
        };
        zr.on('mousedown', handleMouseDown);
        zr.on('mousemove', handleMouseMove);
        window.addEventListener('mousemove', handleWindowMouseMove);
        window.addEventListener('mouseup', handleWindowMouseUp);

        const resizeObserver = new ResizeObserver(() => instance.resize());
        resizeObserver.observe(container);
        return () => {
            window.removeEventListener('mousemove', handleWindowMouseMove);
            window.removeEventListener('mouseup', handleWindowMouseUp);
            resizeObserver.disconnect();
            instance.dispose();
            chart = null;
        };
    });

    $effect(() => {
        if (!chart) return;
        // While dragging, preview the prospective selection.
        chart.setOption(buildHistogramOption(data, dragRange ?? selectedRange, { showAxes }), true);
    });

    onDestroy(() => chart?.dispose());
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
