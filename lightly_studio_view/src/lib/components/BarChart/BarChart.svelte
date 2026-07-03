<script lang="ts">
    import { onDestroy } from 'svelte';
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
        /** Chart height in pixels (default 320). Ignored when horizontal (height grows with bar count). */
        heightPx?: number;
        /** Bar orientation (default 'vertical'). */
        orientation?: BarChartOrientation;
        /**
         * Denominator for tooltip percentages. Pass the sum over all
         * categories when `data` is a subset (e.g. top-N); defaults to the
         * sum of `data`.
         */
        totalCount?: number;
        /** Called with the clicked category. */
        onBarClick?: (item: CategoryCount) => void;
    }

    const {
        data,
        heightPx = 320,
        orientation = 'vertical',
        totalCount,
        onBarClick
    }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: echarts.ECharts | null = $state(null);

    const isHorizontal = $derived(orientation === 'horizontal');

    // Fixed per-bar extent so many categories overflow into scroll instead of
    // squeezing bars into unreadability (same pattern as FiftyOne's histograms
    // panel). Vertical bars scroll horizontally; horizontal bars scroll
    // vertically. The +60px/+40px covers the axis gutters.
    const widthPx = $derived(isHorizontal ? undefined : data.length * 28 + 60);
    const chartHeightPx = $derived(isHorizontal ? data.length * 28 + 40 : heightPx);

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
        No data to display.
    </div>
{:else}
    <div
        class="w-full dark:[color-scheme:dark] {isHorizontal ? 'overflow-y-auto' : 'overflow-x-auto'}"
        data-testid="bar-chart"
    >
        <div
            bind:this={container}
            style={isHorizontal
                ? `width: 100%; height: ${chartHeightPx}px;`
                : `width: ${widthPx}px; min-width: 100%; height: ${chartHeightPx}px;`}
        ></div>
    </div>
{/if}
