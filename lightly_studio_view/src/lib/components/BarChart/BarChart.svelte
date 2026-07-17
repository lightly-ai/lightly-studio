<script lang="ts">
    import { onDestroy, type Snippet } from 'svelte';
    import * as echarts from 'echarts/core';
    import { BarChart as EchartsBarChart } from 'echarts/charts';
    import { GridComponent, TooltipComponent } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';
    import { buildEchartsOption, type BarChartOrientation } from './buildEchartsOption';
    import type { CategoryCount } from './types';

    echarts.use([EchartsBarChart, GridComponent, TooltipComponent, CanvasRenderer]);

    interface Props {
        /** Categories rendered in the given order. */
        data: CategoryCount[];
        /** Bar orientation (default 'vertical'). */
        orientation?: BarChartOrientation;
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
    }

    const {
        data,
        orientation = 'vertical',
        maxWidthPx,
        maxHeightPx,
        totalCount,
        onBarClick,
        emptyState
    }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: echarts.ECharts | null = $state(null);

    const isHorizontal = $derived(orientation === 'horizontal');

    // Bars keep a fixed thickness so many categories overflow into scroll instead
    // of squeezing into unreadability (same pattern as FiftyOne's histograms
    // panel). This extent sizes the category axis (width when vertical, height
    // when horizontal); the +40/+60px covers the axis gutters.
    const BAR_THICKNESS_PX = 28;
    const barsExtentPx = $derived(data.length * BAR_THICKNESS_PX + (isHorizontal ? 40 : 60));

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
            if (item) onBarClick?.(item);
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
        chart.setOption(buildEchartsOption(data, { totalCount, orientation }), true);
    });

    onDestroy(() => chart?.dispose());
</script>

{#if data.length === 0}
    <div class="p-8 text-center text-sm text-muted-foreground" data-testid="bar-chart-empty">
        {#if emptyState}
            {@render emptyState()}
        {:else}
            No data to display.
            <br />Check the
            <a
                href="https://docs.lightly.ai/studio/"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary underline-offset-4 hover:underline"
            >
                documentation
            </a>
            to learn how to add data.
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
