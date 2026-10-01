<script lang="ts">
    import type { ECharts } from 'echarts/core';
    import { buildHistogramOption } from '../buildHistogramOption';
    import { createHistogramChart } from '../createHistogramChart';
    import type { HistogramData, HistogramRange, HistogramSeries } from '../types';

    type ValueMode = NonNullable<
        NonNullable<Parameters<typeof buildHistogramOption>[2]>['valueMode']
    >;

    interface Props {
        data: HistogramData;
        series?: HistogramSeries[];
        selectedRange?: HistogramRange;
        heightPx: number;
        showAxes: boolean;
        valueMode: ValueMode;
        onRangeSelect?: (range: HistogramRange) => void;
    }

    const {
        data,
        series = [],
        selectedRange,
        heightPx,
        showAxes,
        valueMode,
        onRangeSelect
    }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: ECharts | null = $state(null);
    let dragStartIndex = $state<number | null>(null);
    let dragCurrentIndex = $state<number | null>(null);

    const dragRange = $derived.by<HistogramRange | undefined>(() => {
        if (dragStartIndex === null || dragCurrentIndex === null) return undefined;
        const lower = Math.min(dragStartIndex, dragCurrentIndex);
        const upper = Math.max(dragStartIndex, dragCurrentIndex);
        return { min: data.binEdges[lower], max: data.binEdges[upper + 1] };
    });

    $effect(() => {
        if (!container) return;
        const setup = createHistogramChart({
            container,
            getBinCount: () => data.counts.length,
            onDragStart: (binIndex) => {
                if (!onRangeSelect) return;
                dragStartIndex = binIndex;
                dragCurrentIndex = binIndex;
            },
            onDragMove: (binIndex) => {
                if (dragStartIndex === null) return;
                dragCurrentIndex = binIndex;
            },
            onDragEnd: () => {
                const range = dragRange;
                dragStartIndex = null;
                dragCurrentIndex = null;
                if (range) onRangeSelect?.(range);
            }
        });
        chart = setup.chart;
        return () => {
            setup.destroy();
            chart = null;
        };
    });

    $effect(() => {
        if (!chart) return;
        chart.setOption(
            buildHistogramOption(data, dragRange ?? selectedRange, { showAxes, valueMode, series }),
            true
        );
    });
</script>

<div
    bind:this={container}
    class="w-full select-none dark:[color-scheme:dark]"
    class:cursor-crosshair={onRangeSelect}
    style="height: {heightPx}px"
    data-testid="histogram"
></div>
