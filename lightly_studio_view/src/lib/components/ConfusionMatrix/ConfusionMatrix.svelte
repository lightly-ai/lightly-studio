<script lang="ts">
    import { onDestroy } from 'svelte';
    import * as echarts from 'echarts';
    import type { ConfusionMatrixCell, ConfusionMatrixLabelView } from '$lib/api/evaluationRunApi';

    const {
        cells,
        labels
    }: {
        cells: ConfusionMatrixCell[];
        labels: ConfusionMatrixLabelView[];
    } = $props();

    const UNMATCHED = '__unmatched__';

    let container: HTMLDivElement | undefined = $state();
    let chart = $state<echarts.ECharts | null>(null);

    const labelMap = $derived(new Map(labels.map((l) => [l.label_id, l.label_name])));

    function labelName(id: string): string {
        if (id === UNMATCHED) return '—';
        return labelMap.get(id) ?? id.slice(0, 8);
    }

    const sortFn = (a: string, b: string) => {
        if (a === UNMATCHED) return 1;
        if (b === UNMATCHED) return -1;
        return (labelMap.get(a) ?? a).localeCompare(labelMap.get(b) ?? b);
    };

    // Use a single unified label set for both axes so the diagonal is always TP
    const allLabelIds = $derived.by(() => {
        const ids = new Set<string>();
        for (const c of cells) {
            ids.add(c.gt_label_id ?? UNMATCHED);
            ids.add(c.pred_label_id ?? UNMATCHED);
        }
        return [...ids].sort(sortFn);
    });

    const gtLabelIds = $derived(allLabelIds);
    const predLabelIds = $derived(allLabelIds);

    const maxCount = $derived(Math.max(...cells.map((c) => c.count), 1));

    // Init chart when container is available
    $effect(() => {
        if (!container) return;
        const ch = echarts.init(container, null, { renderer: 'canvas' });
        chart = ch;

        const ro = new ResizeObserver(() => ch.resize());
        ro.observe(container);

        return () => {
            ro.disconnect();
            ch.dispose();
            chart = null;
        };
    });

    // Update chart options when data or chart instance changes
    $effect(() => {
        if (!chart) return;

        const predLabels = predLabelIds.map(labelName);
        // Reverse so that index 0 (first label) appears at the top
        const gtLabelsReversed = [...gtLabelIds.map(labelName)].reverse();

        const tpData: [string, string, number][] = [];
        const fpData: [string, string, number][] = [];

        for (const c of cells) {
            const gt = labelName(c.gt_label_id ?? UNMATCHED);
            const pred = labelName(c.pred_label_id ?? UNMATCHED);
            const isDiag =
                c.gt_label_id !== null &&
                c.pred_label_id !== null &&
                c.gt_label_id === c.pred_label_id;
            if (isDiag) {
                tpData.push([pred, gt, c.count]);
            } else {
                fpData.push([pred, gt, c.count]);
            }
        }

        chart.setOption(
            {
                backgroundColor: 'transparent',
                tooltip: {
                    trigger: 'item',
                    formatter: (params: { value: [string, string, number] }) => {
                        const [pred, gt, count] = params.value;
                        return `GT: <b>${gt}</b><br/>Pred: <b>${pred}</b><br/>Count: <b>${count}</b>`;
                    }
                },
                grid: { left: 160, right: 20, top: 10, bottom: 150 },
                xAxis: {
                    type: 'category',
                    data: predLabels,
                    position: 'bottom',
                    axisLabel: {
                        rotate: 45,
                        interval: 0,
                        color: '#9ca3af',
                        fontSize: 13
                    },
                    axisLine: { lineStyle: { color: '#374151' } },
                    splitArea: { show: false }
                },
                yAxis: {
                    type: 'category',
                    data: gtLabelsReversed,
                    axisLabel: { interval: 0, color: '#9ca3af', fontSize: 13 },
                    axisLine: { lineStyle: { color: '#374151' } },
                    splitArea: { show: false }
                },
                dataZoom: [
                    { type: 'inside', xAxisIndex: 0, filterMode: 'empty' },
                    { type: 'inside', yAxisIndex: 0, filterMode: 'empty' }
                ],
                visualMap: [
                    {
                        seriesIndex: 0,
                        min: 1,
                        max: maxCount,
                        inRange: { color: ['rgba(34,197,94,0.15)', 'rgba(34,197,94,0.95)'] },
                        show: false
                    },
                    {
                        seriesIndex: 1,
                        min: 1,
                        max: maxCount,
                        inRange: { color: ['rgba(239,68,68,0.15)', 'rgba(239,68,68,0.95)'] },
                        show: false
                    }
                ],
                series: [
                    {
                        type: 'heatmap',
                        name: 'TP',
                        data: tpData,
                        label: { show: false },
                        emphasis: {
                            itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.4)' }
                        }
                    },
                    {
                        type: 'heatmap',
                        name: 'FP/FN',
                        data: fpData,
                        label: { show: false },
                        emphasis: {
                            itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.4)' }
                        }
                    }
                ]
            },
            true
        );
    });

    onDestroy(() => {
        chart?.dispose();
    });
</script>

<div
    bind:this={container}
    class="w-full"
    style="height: {Math.max(320, allLabelIds.length * 48 + 180)}px;"
></div>
