<script lang="ts">
    import { onDestroy } from 'svelte';
    import * as echarts from 'echarts/core';
    import { HeatmapChart } from 'echarts/charts';
    import {
        DataZoomInsideComponent,
        GridComponent,
        TooltipComponent,
        VisualMapComponent
    } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';
    import { buildEchartsOption } from './buildEchartsOption';
    import ConfusionMatrixLegend from './ConfusionMatrixLegend.svelte';
    import type { ConfusionMatrix } from './types';

    echarts.use([
        HeatmapChart,
        TooltipComponent,
        VisualMapComponent,
        GridComponent,
        DataZoomInsideComponent,
        CanvasRenderer
    ]);

    interface Props {
        matrix: ConfusionMatrix;
        showLegend?: boolean;
        /** Enables inside (scroll/pinch) zoom on both axes. */
        zoomable?: boolean;
    }

    const { matrix, showLegend = false, zoomable = false }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: echarts.ECharts | null = $state(null);

    // 320px floor keeps small matrices readable; 18px per row + 210px for axis/grid margins
    const heightPx = $derived(Math.max(320, matrix.row_labels.length * 18 + 210));

    const maxCount = $derived(
        Math.max(1, ...matrix.counts.flatMap((row) => row).filter((n) => n > 0))
    );

    $effect(() => {
        if (!container) return;
        const instance = echarts.init(container, null, { renderer: 'canvas' });
        chart = instance;
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
        chart.setOption(buildEchartsOption(matrix, { zoomable }), true);
    });

    onDestroy(() => chart?.dispose());
</script>

{#if matrix.row_labels.length === 0}
    <div class="p-8 text-center text-sm text-muted-foreground" data-testid="confusion-matrix-empty">
        No pairing metrics for this run.
    </div>
{:else}
    <div
        bind:this={container}
        class="w-full"
        style="height: {heightPx}px;"
        data-testid="confusion-matrix"
    ></div>
    {#if showLegend}
        <ConfusionMatrixLegend {maxCount} />
    {/if}
{/if}
