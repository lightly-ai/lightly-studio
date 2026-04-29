<script lang="ts">
    import type { EvaluationResultView } from '$lib/api/lightly_studio_local';
    import * as Plot from '@observablehq/plot';
    import {
        chartPalette,
        getActiveComparisonLabels,
        getChartSeriesValue,
        metricRows,
        type EvaluationViewMode
    } from './evaluationDashboard';
    import { plotZoom } from './plotZoom';

    let {
        result,
        mode,
        modelNames,
        selectedModel,
        selectedSubset,
        subsetNames
    }: {
        result: EvaluationResultView;
        mode: EvaluationViewMode;
        modelNames: string[];
        selectedModel: string;
        selectedSubset: string;
        subsetNames: string[];
    } = $props();

    const activeLabels = $derived(getActiveComparisonLabels({ mode, modelNames, subsetNames }));

    const plotData = $derived(
        metricRows.flatMap((metric) =>
            activeLabels.map((label) => ({
                metric: metric.label,
                series: label,
                value: getChartSeriesValue({
                    result,
                    mode,
                    seriesLabel: label,
                    selectedModel,
                    selectedSubset,
                    metricKey: metric.key
                })
            }))
        )
    );

    let container: HTMLElement | undefined = $state();

    $effect(() => {
        if (!container) return;
        const plot = Plot.plot({
            width: container.clientWidth || 640,
            height: 280,
            marginBottom: 40,
            marginLeft: 48,
            style: { background: 'none', color: 'inherit', fontFamily: 'inherit', fontSize: '12px' },
            color: {
                domain: activeLabels,
                range: chartPalette.slice(0, activeLabels.length),
                legend: false
            },
            fx: { label: null, tickSize: 0, padding: 0.2 },
            x: { axis: null },
            y: {
                tickFormat: (d: number) => `${Math.round(d * 100)}%`,
                label: null,
                domain: [0, 1],
                grid: true,
                ticks: 5
            },
            marks: [
                Plot.barY(plotData, {
                    fx: 'metric',
                    x: 'series',
                    y: 'value',
                    fill: 'series',
                    rx: 3,
                    tip: true
                }),
                Plot.ruleY([0])
            ]
        });
        container.replaceChildren(plot);
        return () => container?.replaceChildren();
    });
</script>

<div class="rounded-xl border border-border bg-background p-4">
    <div class="mb-3">
        <h3 class="font-medium">Metric Comparison</h3>
        <p class="text-sm text-muted-foreground">
            {mode === 'models'
                ? `Comparing models on subset "${selectedSubset}".`
                : `Comparing subsets for model "${selectedModel}".`}
        </p>
    </div>

    <div bind:this={container} use:plotZoom class="w-full overflow-hidden rounded-lg"></div>
    <p class="mt-1 text-right text-[10px] text-muted-foreground">scroll to zoom · drag to pan · double-click to reset</p>

    <div class="mt-2 flex flex-wrap gap-3">
        {#each activeLabels as label, i}
            <div class="flex items-center gap-2 text-sm">
                <span class="size-3 rounded-full" style={`background:${chartPalette[i % chartPalette.length]}`}></span>
                <span class="text-muted-foreground">{label}</span>
            </div>
        {/each}
    </div>
</div>
