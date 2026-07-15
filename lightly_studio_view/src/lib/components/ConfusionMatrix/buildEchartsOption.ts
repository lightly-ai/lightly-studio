import type { EChartsCoreOption } from 'echarts/core';
import { CHART_AXIS_LABEL, CHART_EMPHASIS, CHART_LINE_COLOR, CHART_TEXT_COLOR } from '$lib/utils';
import { SENTINELS } from './topNMatrix';
import { type ConfusionMatrix } from './types';

const TP_COLOR_RAMP: [string, string] = ['rgba(34,197,94,0.15)', 'rgba(34,197,94,0.95)'];
const FP_FN_COLOR_RAMP: [string, string] = ['rgba(239,68,68,0.15)', 'rgba(239,68,68,0.95)'];

interface BuildEchartsOptionOptions {
    /** Enables inside (scroll/pinch) zoom on both axes. */
    zoomable?: boolean;
    /**
     * Color intensity multiplier (> 0, default 1). Values > 1 saturate
     * cells earlier (more intense); values < 1 keep cells paler.
     */
    colorIntensity?: number;
    /**
     * Map color from log10(count) instead of the raw count (default true).
     * Log scaling keeps small counts visible next to huge diagonal cells.
     */
    logScale?: boolean;
}

// TP and FP/FN are split into two series with separate visualMaps so each
// can use its own color ramp (ECharts can't color cells in a single heatmap
// series along two scales).
export function buildEchartsOption(
    matrix: ConfusionMatrix,
    options: BuildEchartsOptionOptions = {}
): EChartsCoreOption {
    const xLabels = matrix.col_labels;
    const yLabels = [...matrix.row_labels].reverse();

    // Cells carry [pred, gt, count, log10(count)]. Color maps to the log
    // dimension so a few huge cells don't wash out all smaller counts;
    // tooltips still read the raw count.
    const tpData: [string, string, number, number][] = [];
    const fpFnData: [string, string, number, number][] = [];
    let maxCount = 1;

    for (let i = 0; i < matrix.row_labels.length; i++) {
        for (let j = 0; j < matrix.col_labels.length; j++) {
            const count = matrix.counts[i][j];
            if (count <= 0) continue;
            maxCount = Math.max(maxCount, count);
            const rowLabel = matrix.row_labels[i];
            const colLabel = matrix.col_labels[j];
            const isTrueClassPair = !SENTINELS.has(rowLabel) && !SENTINELS.has(colLabel);
            const isTp = isTrueClassPair && rowLabel === colLabel;
            (isTp ? tpData : fpFnData).push([colLabel, rowLabel, count, Math.log10(count)]);
        }
    }

    // Falls back to 1 when all counts are <= 1 so the visualMap range stays valid.
    const logMaxCount = maxCount > 1 ? Math.log10(maxCount) : 1;
    // Dividing the range by the intensity makes cells hit full color sooner.
    const colorIntensity = Math.max(options.colorIntensity ?? 1, 0.01);
    const logScale = options.logScale ?? true;
    // Dimension 3 is log10(count), dimension 2 the raw count.
    const visualMapDimension = logScale ? 3 : 2;
    const visualMapMin = logScale ? 0 : 1;
    // Clamp to the min so a high colorIntensity can't push the max below it,
    // which would produce an invalid/reversed range (e.g. min: 1, max: 0.5).
    const visualMapMax = Math.max(
        (logScale ? logMaxCount : maxCount) / colorIntensity,
        visualMapMin
    );

    const nameGap = 20;
    return {
        backgroundColor: 'transparent',
        ...(options.zoomable && {
            dataZoom: [
                { type: 'inside', xAxisIndex: 0 },
                { type: 'inside', yAxisIndex: 0, orient: 'vertical' }
            ]
        }),
        tooltip: {
            trigger: 'item',
            formatter: (params: { value: [string, string, number] }) => {
                const [pred, gt, count] = params.value;
                return `GT: <b>${gt}</b><br/>Pred: <b>${pred}</b><br/>Count: <b>${count}</b>`;
            }
        },
        grid: { left: 0, right: 0, top: 0, bottom: 100 },
        xAxis: {
            type: 'category',
            data: xLabels,
            position: 'bottom',
            name: 'Prediction',
            nameLocation: 'middle',
            nameGap,
            nameTextStyle: { color: CHART_TEXT_COLOR, fontSize: 13, fontWeight: 'bold' },
            axisLabel: { ...CHART_AXIS_LABEL, rotate: 45, interval: 0 },
            axisLine: { lineStyle: { color: CHART_LINE_COLOR } },
            splitArea: { show: false }
        },
        yAxis: {
            type: 'category',
            data: yLabels,
            name: 'Ground Truth',
            nameLocation: 'middle',
            nameGap,
            nameRotate: 90,
            nameTextStyle: { color: CHART_TEXT_COLOR, fontSize: 13, fontWeight: 'bold' },
            axisLabel: { ...CHART_AXIS_LABEL, interval: 0 },
            axisLine: { lineStyle: { color: CHART_LINE_COLOR } },
            splitArea: { show: false }
        },
        visualMap: [
            {
                seriesIndex: 0,
                dimension: visualMapDimension,
                min: visualMapMin,
                max: visualMapMax,
                inRange: { color: TP_COLOR_RAMP },
                show: false
            },
            {
                seriesIndex: 1,
                dimension: visualMapDimension,
                min: visualMapMin,
                max: visualMapMax,
                inRange: { color: FP_FN_COLOR_RAMP },
                show: false
            }
        ],
        series: [
            {
                type: 'heatmap',
                name: 'TP',
                data: tpData,
                label: { show: false },
                emphasis: CHART_EMPHASIS
            },
            {
                type: 'heatmap',
                name: 'FP/FN',
                data: fpFnData,
                label: { show: false },
                emphasis: CHART_EMPHASIS
            }
        ]
    };
}
