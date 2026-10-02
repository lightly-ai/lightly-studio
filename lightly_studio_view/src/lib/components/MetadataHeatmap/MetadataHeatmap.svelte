<script lang="ts">
    import type { ECharts } from 'echarts/core';
    import { buildHeatmapOption } from './buildHeatmapOption';
    import { rectFromAxisLabel, rectFromCells, selectionFromRect } from './cellRect';
    import { createHeatmapChart } from './createHeatmapChart';
    import type { HeatmapAxis, HeatmapCell, HeatmapCellRect, HeatmapSelection } from './types';

    interface Props {
        xAxis: HeatmapAxis;
        yAxis: HeatmapAxis;
        /** Counts indexed as `counts[y][x]`. */
        counts: number[][];
        /** Cells outside the selection are dimmed. `null` dims no cell. */
        selection: HeatmapSelection | null;
        heightPx: number;
        valueNoun?: string;
        /** Called with the clicked cell, the dragged rectangle, or the row/column of a label. */
        onSelect?: (rect: HeatmapCellRect) => void;
    }

    const {
        xAxis,
        yAxis,
        counts,
        selection,
        heightPx,
        valueNoun = 'samples',
        onSelect
    }: Props = $props();

    let container: HTMLDivElement | undefined = $state();
    let chart: ECharts | null = $state(null);
    let dragStart = $state<HeatmapCell | null>(null);
    let dragEnd = $state<HeatmapCell | null>(null);

    const dragRect = $derived(dragStart && dragEnd ? rectFromCells(dragStart, dragEnd) : null);
    // The dragged rectangle previews the selection until the pointer is released.
    const shownSelection = $derived(dragRect ? selectionFromRect(dragRect) : selection);
    const gridSize = () => ({ xCount: xAxis.labels.length, yCount: yAxis.labels.length });

    $effect(() => {
        if (!container) return;
        const setup = createHeatmapChart({
            container,
            getGridSize: gridSize,
            onDragStart: (cell) => {
                if (!onSelect) return;
                dragStart = cell;
                dragEnd = cell;
            },
            onDragMove: (cell) => {
                if (dragStart) dragEnd = cell;
            },
            onDragEnd: () => {
                const rect = dragRect;
                dragStart = null;
                dragEnd = null;
                if (rect) onSelect?.(rect);
            },
            onAxisLabelClick: (axis, index) =>
                onSelect?.(rectFromAxisLabel(axis, index, gridSize()))
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
            buildHeatmapOption({ xAxis, yAxis, counts, selection: shownSelection, valueNoun }),
            true
        );
    });
</script>

<div
    bind:this={container}
    class="w-full select-none dark:[color-scheme:dark]"
    class:cursor-crosshair={onSelect}
    style="height: {heightPx}px"
    data-testid="metadata-heatmap"
></div>
