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
    import { buildEchartsOption, unifyLabels } from './buildEchartsOption';
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
    }

    const { matrix, showLegend = false }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: echarts.ECharts | null = $state(null);

    const rowCount = $derived(unifyLabels(matrix.row_labels, matrix.col_labels).length);
    const heightPx = $derived(Math.max(320, rowCount * 48 + 180));

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
        chart.setOption(buildEchartsOption(matrix), true);
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
