import type { EChartsCoreOption } from 'echarts/core';
import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL, type ConfusionMatrix } from './types';

const TP_COLOR_RAMP: [string, string] = ['rgba(34,197,94,0.15)', 'rgba(34,197,94,0.95)'];
const FP_FN_COLOR_RAMP: [string, string] = ['rgba(239,68,68,0.15)', 'rgba(239,68,68,0.95)'];
const SENTINEL_LABELS = new Set<string>([NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL]);

// TP and FP/FN are split into two series with separate visualMaps so each
// can use its own color ramp (ECharts can't color cells in a single heatmap
// series along two scales).
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

    const nameGap = 20;
    return {
        backgroundColor: 'transparent',
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
            nameTextStyle: { color: '#9ca3af', fontSize: 13, fontWeight: 'bold' },
            axisLabel: { rotate: 45, interval: 0, color: '#9ca3af', fontSize: 12 },
            axisLine: { lineStyle: { color: '#374151' } },
            splitArea: { show: false }
        },
        yAxis: {
            type: 'category',
            data: yLabels,
            name: 'Ground Truth',
            nameLocation: 'middle',
            nameGap,
            nameRotate: 90,
            nameTextStyle: { color: '#9ca3af', fontSize: 13, fontWeight: 'bold' },
            axisLabel: { interval: 0, color: '#9ca3af', fontSize: 12 },
            axisLine: { lineStyle: { color: '#374151' } },
            splitArea: { show: false }
        },
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
