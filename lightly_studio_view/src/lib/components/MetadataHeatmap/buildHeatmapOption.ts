import type { EChartsCoreOption } from 'echarts/core';
import escape from 'lodash-es/escape';
import { CHART_AXIS_LABEL, CHART_EMPHASIS, CHART_LINE_COLOR, formatInteger } from '$lib/utils';
import type { HeatmapAxis, HeatmapSelection } from './types';

// The Lightly primary green, the accent of the histogram and the bar chart.
const SELECTED_COLOR_RAMP: [string, string] = ['rgba(59,217,159,0.2)', 'rgba(59,217,159,1)'];
// Gray-600, the dimmed color of the histogram, for cells outside the selection.
const DIMMED_COLOR_RAMP: [string, string] = ['rgba(75,85,99,0.25)', 'rgba(75,85,99,0.7)'];
// Count labels fit only in the cells of small grids.
const MAX_LABELED_CELLS = 64;
// Rotate the x labels when they cannot all fit side by side.
const MAX_UNROTATED_X_LABELS = 6;

/** A heatmap data item: the bucket indices, the count, and log10 of the count. */
type HeatmapItem = [x: number, y: number, count: number, logCount: number];

interface BuildHeatmapOptionParams {
    xAxis: HeatmapAxis;
    yAxis: HeatmapAxis;
    /** Counts indexed as `counts[y][x]`. */
    counts: number[][];
    /** Cells outside the selection are dimmed. `null` dims no cell. */
    selection: HeatmapSelection | null;
    /** The counted unit in the tooltip, for example "samples". */
    valueNoun: string;
}

/**
 * Builds the ECharts option of a metadata heatmap. Cells are indexed by bucket, not
 * by label, so that equal labels cannot merge two buckets. The selected and the
 * dimmed cells are two series with their own color ramp, because one heatmap series
 * cannot color its cells along two scales.
 */
export function buildHeatmapOption({
    xAxis,
    yAxis,
    counts,
    selection,
    valueNoun
}: BuildHeatmapOptionParams): EChartsCoreOption {
    const selectedItems: HeatmapItem[] = [];
    const dimmedItems: HeatmapItem[] = [];
    let maxCount = 1;
    counts.forEach((row, y) =>
        row.forEach((count, x) => {
            if (count <= 0) return;
            maxCount = Math.max(maxCount, count);
            const items = isCellSelected(selection, x, y) ? selectedItems : dimmedItems;
            items.push([x, y, count, Math.log10(count)]);
        })
    );
    // Color follows log10(count), so a few large cells do not wash out the small ones.
    const logMaxCount = maxCount > 1 ? Math.log10(maxCount) : 1;
    const showLabels = xAxis.labels.length * yAxis.labels.length <= MAX_LABELED_CELLS;
    const rotateXLabels = xAxis.labels.length > MAX_UNROTATED_X_LABELS;

    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            formatter: ({ value }: { value: HeatmapItem }) =>
                `${escape(xAxis.name)}: <b>${escape(xAxis.labels[value[0]])}</b><br/>` +
                `${escape(yAxis.name)}: <b>${escape(yAxis.labels[value[1]])}</b><br/>` +
                `${formatInteger(value[2])} ${escape(valueNoun)}`
        },
        grid: { left: 8, right: 16, top: 8, bottom: 8, containLabel: true },
        xAxis: {
            ...categoryAxis(xAxis),
            axisLabel: { ...CHART_AXIS_LABEL, interval: 0, rotate: rotateXLabels ? 45 : 0 }
        },
        // Inverse keeps the first bucket at the top, so `counts[y]` is the y-th row.
        yAxis: { ...categoryAxis(yAxis), inverse: true },
        visualMap: [
            visualMap(0, SELECTED_COLOR_RAMP, logMaxCount),
            visualMap(1, DIMMED_COLOR_RAMP, logMaxCount)
        ],
        series: [
            heatmapSeries('Selected', selectedItems, showLabels),
            heatmapSeries('Not selected', dimmedItems, showLabels)
        ]
    };
}

export function isCellSelected(selection: HeatmapSelection | null, x: number, y: number): boolean {
    if (!selection) return true;
    return (
        (selection.x === null || selection.x.includes(x)) &&
        (selection.y === null || selection.y.includes(y))
    );
}

function categoryAxis(axis: HeatmapAxis) {
    return {
        type: 'category',
        data: axis.labels,
        // Axis label clicks select a full row or column.
        triggerEvent: true,
        axisLabel: { ...CHART_AXIS_LABEL, interval: 0 },
        axisLine: { lineStyle: { color: CHART_LINE_COLOR } },
        splitArea: { show: false }
    };
}

function visualMap(seriesIndex: number, colors: [string, string], max: number) {
    // Dimension 3 of an item is log10(count).
    return { seriesIndex, dimension: 3, min: 0, max, inRange: { color: colors }, show: false };
}

function heatmapSeries(name: string, data: HeatmapItem[], showLabels: boolean) {
    return {
        type: 'heatmap',
        name,
        data,
        label: {
            show: showLabels,
            color: '#f9fafb',
            fontSize: 10,
            formatter: ({ value }: { value: HeatmapItem }) => formatInteger(value[2])
        },
        emphasis: CHART_EMPHASIS
    };
}
