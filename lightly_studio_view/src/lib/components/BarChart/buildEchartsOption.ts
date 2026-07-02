import type { EChartsCoreOption } from 'echarts/core';
import type { CategoryCount } from './types';

// Single accent color (the Lightly primary green, --color-lightly-primary #3bd99f):
// per-class colors carry no meaning in a count distribution, mirroring FiftyOne's
// histograms panel.
const BAR_COLOR = 'rgba(59,217,159,0.85)';

const MAX_LABEL_CHARS = 24;

/** Truncates long category names on the axis; the tooltip shows the full name. */
export function truncateLabel(label: string): string {
    return label.length > MAX_LABEL_CHARS ? `${label.slice(0, MAX_LABEL_CHARS - 1)}…` : label;
}

function formatPercent(ratio: number): string {
    const percent = ratio * 100;
    if (percent > 0 && percent < 0.1) return '<0.1%';
    return `${percent.toFixed(1)}%`;
}

interface BuildEchartsOptionOptions {
    /**
     * Denominator for tooltip percentages. Pass the sum over all categories
     * when `data` is a subset (e.g. top-N), so percentages stay relative to
     * the full dataset. Defaults to the sum of `data`.
     */
    totalCount?: number;
}

export function buildEchartsOption(
    data: CategoryCount[],
    options: BuildEchartsOptionOptions = {}
): EChartsCoreOption {
    const totalCount = options.totalCount ?? data.reduce((sum, item) => sum + item.count, 0);
    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: { name: string; value: number }[]) => {
                const [{ name, value }] = params;
                const percent = totalCount > 0 ? ` (${formatPercent(value / totalCount)})` : '';
                return `<b>${name}</b><br/>Count: <b>${value}</b>${percent}`;
            }
        },
        grid: { left: 8, right: 8, top: 16, bottom: 8, containLabel: true },
        xAxis: {
            type: 'category',
            data: data.map((item) => item.label),
            axisLabel: {
                // Steep rotation keeps long rotated labels from overflowing the
                // left canvas edge (echarts containLabel ignores rotation).
                rotate: 60,
                interval: 0,
                color: '#9ca3af',
                fontSize: 12,
                formatter: truncateLabel
            },
            axisLine: { lineStyle: { color: '#374151' } },
            axisTick: { alignWithLabel: true }
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: '#9ca3af', fontSize: 12 },
            splitLine: { lineStyle: { color: '#374151' } }
        },
        series: [
            {
                type: 'bar',
                data: data.map((item) => item.count),
                itemStyle: { color: BAR_COLOR },
                barCategoryGap: '25%',
                emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.3)' } }
            }
        ]
    };
}
