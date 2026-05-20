import type { EChartsCoreOption } from 'echarts/core';
import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL, type ConfusionMatrix } from './types';

const TP_COLOR_RAMP: [string, string] = ['rgba(34,197,94,0.15)', 'rgba(34,197,94,0.95)'];
const FP_FN_COLOR_RAMP: [string, string] = ['rgba(239,68,68,0.15)', 'rgba(239,68,68,0.95)'];
const SENTINEL_LABELS = new Set<string>([NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL]);

/**
 * Build the ECharts option object for a confusion matrix. Pulled out of
 * the component for testability and to keep the .svelte file under the
 * 100-line guideline.
 *
 * Encoding follows the proto on `jonas-model-eval-cvpr-proto`:
 * - Unified label set on both axes so the diagonal aligns.
 * - Two heatmap series with independent `visualMap`s: TP cells get a green
 *   ramp, FP/FN cells get a red ramp. The diagonal pops without any
 *   explicit cell-border decoration.
 * - Color intensity scales with absolute count, capped at the matrix max.
 * - Y-axis reversed so the first sorted label sits at the top.
 */
export function buildEchartsOption(matrix: ConfusionMatrix): EChartsCoreOption {
    const xLabels = matrix.col_labels;
    const yLabels = [...matrix.row_labels].reverse();

    const tpData: [string, string, number][] = [];
    const fpFnData: [string, string, number][] = [];
    let maxCount = 1;

    for (let i = 0; i < matrix.row_labels.length; i++) {
        for (let j = 0; j < matrix.col_labels.length; j++) {
            const count = matrix.counts[i][j];
            if (count <= 0) continue;
            maxCount = Math.max(maxCount, count);
            const rowLabel = matrix.row_labels[i];
            const colLabel = matrix.col_labels[j];
            const isTrueClassPair =
                !SENTINEL_LABELS.has(rowLabel) && !SENTINEL_LABELS.has(colLabel);
            const isTp = isTrueClassPair && rowLabel === colLabel;
            (isTp ? tpData : fpFnData).push([colLabel, rowLabel, count]);
        }
    }

    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            formatter: (params: { value: [string, string, number] }) => {
                const [pred, gt, count] = params.value;
                return `GT: <b>${gt}</b><br/>Pred: <b>${pred}</b><br/>Count: <b>${count}</b>`;
            }
        },
        grid: { left: 160, right: 24, top: 16, bottom: 150 },
        xAxis: {
            type: 'category',
            data: xLabels,
            position: 'bottom',
            axisLabel: { rotate: 45, interval: 0, color: '#9ca3af', fontSize: 12 },
            axisLine: { lineStyle: { color: '#374151' } },
            splitArea: { show: false }
        },
        yAxis: {
            type: 'category',
            data: yLabels,
            axisLabel: { interval: 0, color: '#9ca3af', fontSize: 12 },
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
                inRange: { color: TP_COLOR_RAMP },
                show: false
            },
            {
                seriesIndex: 1,
                min: 1,
                max: maxCount,
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
                emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.3)' } }
            },
            {
                type: 'heatmap',
                name: 'FP/FN',
                data: fpFnData,
                label: { show: false },
                emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.3)' } }
            }
        ]
    };
}
