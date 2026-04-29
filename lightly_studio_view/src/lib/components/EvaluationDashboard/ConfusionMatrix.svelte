<script lang="ts">
    import type { ConfusionMatrix, EvaluationResultView } from '$lib/api/lightly_studio_local';
    import * as Plot from '@observablehq/plot';
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

    type MatrixEntry = { label: string; color: string; data: ConfusionMatrix | null };

    const matrices = $derived(
        mode === 'models'
            ? modelNames.map((name, i) => ({
                  label: name,
                  color: chartPalette[i % chartPalette.length],
                  data: (result.metrics[name]?.[selectedSubset]
                      ?.confusion_matrix as ConfusionMatrix | null | undefined) ?? null
              }))
            : subsetNames.map((subset, i) => ({
                  label: subset,
                  color: chartPalette[i % chartPalette.length],
                  data: (result.metrics[selectedModel]?.[subset]
                      ?.confusion_matrix as ConfusionMatrix | null | undefined) ?? null
              }))
    );

    const hasData = $derived(matrices.some((m) => m.data && m.data.labels.length > 0));

    /** Parse hex → rgba string for a given alpha 0–1. */
    function hexRgba(hex: string, alpha: number): string {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r},${g},${b},${alpha})`;
    }

    function buildPlot(entry: MatrixEntry, containerWidth: number): SVGElement | HTMLElement {
        const { labels, matrix } = entry.data!;
        const maxCount = Math.max(1, ...matrix.flat());

        const cells = labels.flatMap((gt, ri) =>
            labels.map((pred, ci) => ({ gt, pred, count: matrix[ri][ci] }))
        );

        const cellSize = Math.max(28, Math.min(48, Math.floor((containerWidth - 120) / labels.length)));

        return Plot.plot({
            width: 120 + labels.length * cellSize,
            height: 80 + labels.length * cellSize,
            marginTop: 80,
            marginLeft: 100,
            marginBottom: 32,
            marginRight: 10,
            style: { background: 'none', color: 'inherit', fontFamily: 'inherit', fontSize: '11px' },
            x: { label: 'Predicted', tickSize: 0, tickRotate: -40 },
            y: { label: 'GT', tickSize: 0 },
            color: {
                type: 'linear',
                domain: [0, maxCount],
                range: [hexRgba(entry.color, 0.06), entry.color]
            },
            marks: [
                Plot.cell(cells, {
                    x: 'pred',
                    y: 'gt',
                    fill: 'count',
                    inset: 1,
                    rx: 3
                }),
                Plot.text(cells, {
                    x: 'pred',
                    y: 'gt',
                    text: (d: { count: number }) => (d.count > 0 ? String(d.count) : ''),
                    fill: (d: { count: number }) =>
                        d.count / maxCount > 0.55 ? 'white' : 'currentColor',
                    fontSize: Math.max(9, cellSize * 0.3)
                })
            ]
        });
    }

    // One ref per matrix entry — use an action so we can re-render on data change.
    function matrixPlot(node: HTMLElement, entry: MatrixEntry) {
        function render(e: MatrixEntry) {
            if (!e.data || e.data.labels.length === 0) return;
            node.replaceChildren(buildPlot(e, node.clientWidth || 600));
        }
        render(entry);
        return {
            update: render,
            destroy: () => node.replaceChildren()
        };
    }
</script>

{#if hasData}
    <div class="rounded-xl border border-border bg-background p-4">
        <div class="mb-4">
            <h3 class="font-medium">Confusion Matrices</h3>
            <p class="text-sm text-muted-foreground">
                {mode === 'models'
                    ? `Subset "${selectedSubset}" — one matrix per model.`
                    : `Model "${selectedModel}" — one matrix per subset.`}
                Rows = GT class, columns = predicted class.
            </p>
        </div>

        <div class="flex flex-col gap-8">
            {#each matrices as entry}
                {#if entry.data && entry.data.labels.length > 0}
                    <div>
                        <div class="mb-2 flex items-center gap-2 text-sm font-medium">
                            <span
                                class="size-3 rounded-full"
                                style={`background:${entry.color}`}
                            ></span>
                            {entry.label}
                        </div>
                        <div use:plotZoom class="overflow-hidden rounded-lg">
                            <div use:matrixPlot={entry}></div>
                        </div>
                        <p class="mt-1 text-right text-[10px] text-muted-foreground">scroll to zoom · drag to pan · double-click to reset</p>
                    </div>
                {/if}
            {/each}
        </div>
    </div>
{/if}
