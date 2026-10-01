<script lang="ts">
    import { onDestroy, type Snippet } from 'svelte';
    import * as echarts from 'echarts/core';
    import { BarChart as EchartsBarChart } from 'echarts/charts';
    import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';
    import {
        buildEchartsOption,
        GROUPED_GRID_TOP_PX,
        type BarChartOrientation,
        type BarChartValueMode
    } from './buildEchartsOption';
    import type { CategoryCount, CategoryCountSeries } from './types';

    echarts.use([
        EchartsBarChart,
        GridComponent,
        LegendComponent,
        TooltipComponent,
        CanvasRenderer
    ]);

    interface Props {
        /** Categories rendered in the given order. */
        data: CategoryCount[];
        /** Optional named series rendered as grouped bars on the `data` category axis. */
        series?: CategoryCountSeries[];
        /** Bar orientation (default 'vertical'). */
        orientation?: BarChartOrientation;
        /** Whether bars show raw counts or percentages (default 'number'). */
        valueMode?: BarChartValueMode;
        /**
         * Caps the chart width in px. Vertical bars scroll horizontally once they
         * exceed it; horizontal bars fill it. Defaults to the parent width.
         */
        maxWidthPx?: number;
        /**
         * Caps the chart height in px (default 320). Horizontal bars scroll
         * vertically once they exceed it; vertical bars fill it.
         */
        maxHeightPx?: number;
        /**
         * Denominator for tooltip percentages. Pass the sum over all
         * categories when `data` is a subset (e.g. top-N); defaults to the
         * sum of `data`.
         */
        totalCount?: number;
        /** Called with the clicked category. */
        onBarClick?: (item: CategoryCount) => void;
        /** Custom content shown when data is empty. Replaces the default message. */
        emptyState?: Snippet;
        /** Top chart-grid padding in px (default 16). */
        gridTopPx?: number;
    }

    const {
        data,
        series = [],
        orientation = 'vertical',
        valueMode = 'number',
        maxWidthPx,
        maxHeightPx,
        totalCount,
        onBarClick,
        emptyState,
        gridTopPx
    }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: echarts.ECharts | null = $state(null);

    const isHorizontal = $derived(orientation === 'horizontal');

    // Bars keep a fixed thickness so many categories overflow into scroll instead
    // of squeezing into unreadability (same pattern as FiftyOne's histograms
    // panel). This extent sizes the category axis (width when vertical, height
    // when horizontal); the +40/+60px covers the axis gutters.
    const BAR_THICKNESS_PX = 28;
    const DEFAULT_GRID_TOP_PX = 16;
    const categoryThicknessPx = $derived(Math.max(BAR_THICKNESS_PX, series.length * 14));
    // For grouped horizontal charts, the legend consumes GROUPED_GRID_TOP_PX of
    // vertical space that isn't part of the category axis, so include the delta.
    const groupedLegendHeightPx = $derived(
        isHorizontal && series.length > 0
            ? GROUPED_GRID_TOP_PX - (gridTopPx ?? DEFAULT_GRID_TOP_PX)
            : 0
    );
    const barsExtentPx = $derived(
        data.length * categoryThicknessPx + (isHorizontal ? 40 : 60) + groupedLegendHeightPx
    );

    // Height budget in px: the measured container height, or a fallback so the
    // chart still renders when the parent is unconstrained (standalone/Storybook).
    const heightPx = $derived(maxHeightPx ?? 320);

    // Outer scroll viewport. Vertical bars fill the height budget (the canvas
    // resolves its `height: 100%` against this concrete height); horizontal bars
    // cap there and scroll vertically past it.
    const viewportStyle = $derived(
        [
            isHorizontal ? `max-height: ${heightPx}px` : `height: ${heightPx}px`,
            maxWidthPx ? `max-width: ${maxWidthPx}px` : null
        ]
            .filter(Boolean)
            .join('; ')
    );

    // Inner canvas — ECharts reads these px dimensions. The bars axis grows with
    // the data (scrolling past the viewport); the value axis fills 100%.
    const canvasStyle = $derived(
        isHorizontal
            ? `width: 100%; height: ${barsExtentPx}px;`
            : `width: ${barsExtentPx}px; min-width: 100%; height: 100%;`
    );

    $effect(() => {
        if (!container) return;
        const instance = echarts.init(container, null, { renderer: 'canvas' });
        chart = instance;
        instance.on('click', (params: { dataIndex?: number }) => {
            if (typeof params.dataIndex !== 'number') return;
            const item = data[params.dataIndex];
            if (item && item.selectable !== false) onBarClick?.(item);
        });
        const resizeObserver = new ResizeObserver(() => instance.resize());
        resizeObserver.observe(container);
        return () => {
            resizeObserver.disconnect();
            instance.dispose();
            chart = null;
        };
    });

    $effect(() => {
        if (!chart) return;
        chart.setOption(
            buildEchartsOption(data, {
                totalCount,
                orientation,
                series,
                valueMode,
                gridTopPx
            }),
            true
        );
    });

    onDestroy(() => chart?.dispose());
</script>

{#if data.length === 0}
    <div class="p-8 text-center text-sm text-muted-foreground" data-testid="bar-chart-empty">
        {#if emptyState}
            {@render emptyState()}
        {:else}
            No distribution data to display.
            <br />Add annotations or metadata to see their distribution.
            <br />Learn more in the
            <a
                href="https://docs.lightly.ai/studio/"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary underline-offset-4 hover:underline"
            >
                documentation
            </a>.
        {/if}
    </div>
{:else}
    <div
        class="w-full dark:[color-scheme:dark] {isHorizontal
            ? 'overflow-y-auto'
            : 'overflow-x-auto'}"
        style={viewportStyle}
        data-testid="bar-chart"
    >
        <div bind:this={container} style={canvasStyle}></div>
    </div>
{/if}
