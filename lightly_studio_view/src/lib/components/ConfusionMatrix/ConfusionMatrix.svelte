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
    import {
        NO_GROUND_TRUTH_ROW_LABEL,
        NO_PREDICTION_COL_LABEL,
        type ConfusionCellSelection,
        type ConfusionMatrix
    } from './types';

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
        /** Color intensity multiplier (> 0, default 1). */
        colorIntensity?: number;
        /** Map color from log10(count) instead of the raw count (default true). */
        logScale?: boolean;
        /**
         * Called when a real class-by-class cell is clicked. Synthetic FP/FN cells
         * (no ground truth / no prediction) are ignored and never invoke this.
         */
        onCellClick?: (cell: ConfusionCellSelection) => void;
    }

    const {
        matrix,
        showLegend = false,
        zoomable = false,
        colorIntensity = 1,
        logScale = true,
        onCellClick
    }: Props = $props();

    const SENTINEL_LABELS = new Set<string>([NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL]);

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
        // Cells carry [pred, gt, count, log10(count)]; resolve back to labels and
        // skip the synthetic FP/FN buckets, which are not class-by-class cells.
        instance.on('click', (params: { value?: unknown }) => {
            if (!Array.isArray(params.value)) return;
            const [predLabel, gtLabel] = params.value as [string, string, number, number];
            if (SENTINEL_LABELS.has(predLabel) || SENTINEL_LABELS.has(gtLabel)) return;
            onCellClick?.({ gtLabel, predLabel });
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
        chart.setOption(buildEchartsOption(matrix, { zoomable, colorIntensity, logScale }), true);
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
        <ConfusionMatrixLegend {maxCount} {logScale} />
    {/if}
{/if}
