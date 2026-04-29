<script lang="ts">
    import type { EvaluationResultView, PerClassMetrics } from '$lib/api/lightly_studio_local';
    import * as Plot from '@observablehq/plot';
    import * as Select from '$lib/components/ui/select';
    import { chartPalette, type EvaluationViewMode } from './evaluationDashboard';
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

    type MetricKey = keyof PerClassMetrics;

    const metricOptions: Array<{ key: MetricKey; label: string }> = [
        { key: 'ap', label: 'Average Precision (AP)' },
        { key: 'recall', label: 'Recall' },
        { key: 'f1', label: 'F1-Score' }
    ];

    let selectedMetric = $state<MetricKey>('ap');

    const series = $derived(
        mode === 'models'
            ? modelNames.map((name, i) => ({
                  label: name,
                  color: chartPalette[i % chartPalette.length],
                  data: (result.metrics[name]?.[selectedSubset]?.per_class_metrics ?? {}) as Record<
                      string,
                      PerClassMetrics
                  >
              }))
            : subsetNames.map((subset, i) => ({
                  label: subset,
                  color: chartPalette[i % chartPalette.length],
                  data: (result.metrics[selectedModel]?.[subset]?.per_class_metrics ??
                      {}) as Record<string, PerClassMetrics>
              }))
    );

    const classNames = $derived(
        Array.from(new Set(series.flatMap((s) => Object.keys(s.data)))).sort()
    );

    const plotData = $derived(
        classNames.flatMap((cls) =>
            series.map((s) => ({
                class: cls,
                series: s.label,
                value: s.data[cls]?.[selectedMetric] ?? 0
            }))
        )
    );

    let container: HTMLElement | undefined = $state();

    $effect(() => {
        if (!container || classNames.length === 0) return;
        const seriesLabels = series.map((s) => s.label);
        const plot = Plot.plot({
            width: Math.max(container.clientWidth || 640, classNames.length * seriesLabels.length * 18 + 80),
            height: 280,
            marginBottom: 80,
            marginLeft: 48,
            style: { background: 'none', color: 'inherit', fontFamily: 'inherit', fontSize: '12px' },
            color: {
                domain: seriesLabels,
                range: chartPalette.slice(0, seriesLabels.length),
                legend: false
            },
            fx: { label: null, tickSize: 0, padding: 0.15, tickRotate: -35 },
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
                    fx: 'class',
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

{#if classNames.length > 0}
    <div class="rounded-xl border border-border bg-background p-4">
        <div class="mb-3 flex items-start justify-between gap-4">
            <div>
                <h3 class="font-medium">Per-Class Metrics</h3>
                <p class="text-sm text-muted-foreground">
                    {mode === 'models'
                        ? `Subset "${selectedSubset}" — comparing models by class.`
                        : `Model "${selectedModel}" — comparing subsets by class.`}
                </p>
            </div>
            <Select.Root type="single" bind:value={selectedMetric}>
                <Select.Trigger class="w-[200px] shrink-0">
                    {metricOptions.find((m) => m.key === selectedMetric)?.label ?? selectedMetric}
                </Select.Trigger>
                <Select.Content>
                    {#each metricOptions as opt}
                        <Select.Item value={opt.key} label={opt.label}>{opt.label}</Select.Item>
                    {/each}
                </Select.Content>
            </Select.Root>
        </div>

        <div bind:this={container} use:plotZoom class="w-full overflow-hidden rounded-lg"></div>
        <p class="mt-1 text-right text-[10px] text-muted-foreground">scroll to zoom · drag to pan · double-click to reset</p>

        <div class="mt-2 flex flex-wrap gap-3">
            {#each series as s}
                <div class="flex items-center gap-2 text-sm">
                    <span class="size-3 rounded-full" style={`background:${s.color}`}></span>
                    <span class="text-muted-foreground">{s.label}</span>
                </div>
            {/each}
        </div>
    </div>
{/if}
