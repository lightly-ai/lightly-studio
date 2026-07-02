<script lang="ts">
    import { onDestroy } from 'svelte';
    import * as echarts from 'echarts/core';
    import { BarChart as EchartsBarChart } from 'echarts/charts';
    import { GridComponent, TooltipComponent } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';
    import { buildEchartsOption } from './buildEchartsOption';
    import type { CategoryCount } from './types';

    echarts.use([EchartsBarChart, GridComponent, TooltipComponent, CanvasRenderer]);

    interface Props {
        /** Categories rendered left-to-right in the given order. */
        data: CategoryCount[];
        /** Chart height in pixels (default 320). */
        heightPx?: number;
        /** Called with the clicked category. */
        onBarClick?: (item: CategoryCount) => void;
    }

    const { data, heightPx = 320, onBarClick }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: echarts.ECharts | null = $state(null);

    // Fixed per-bar width so many categories overflow into horizontal scroll
    // instead of squeezing bars into unreadability (same pattern as FiftyOne's
    // histograms panel). 60px covers the y-axis gutter.
    const widthPx = $derived(data.length * 28 + 60);

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
        chart.setOption(buildEchartsOption(data), true);
    });

    onDestroy(() => chart?.dispose());
</script>

{#if data.length === 0}
    <div class="p-8 text-center text-sm text-muted-foreground" data-testid="bar-chart-empty">
        No data to display.
    </div>
{:else}
    <div class="w-full overflow-x-auto" data-testid="bar-chart">
        <div
            bind:this={container}
            style="width: {widthPx}px; min-width: 100%; height: {heightPx}px;"
        ></div>
    </div>
{/if}
