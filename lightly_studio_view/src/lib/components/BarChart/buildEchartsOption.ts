import type { EChartsCoreOption } from 'echarts/core';
import type { CategoryCount } from './types';

// Single accent color (Tailwind blue-500): per-class colors carry no meaning
// in a count distribution, mirroring FiftyOne's histograms panel.
const BAR_COLOR = 'rgba(59,130,246,0.85)';

const MAX_LABEL_CHARS = 24;

/** Truncates long category names on the axis; the tooltip shows the full name. */
export function truncateLabel(label: string): string {
    return label.length > MAX_LABEL_CHARS ? `${label.slice(0, MAX_LABEL_CHARS - 1)}…` : label;
}

export function buildEchartsOption(data: CategoryCount[]): EChartsCoreOption {
    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: { name: string; value: number }[]) => {
                const [{ name, value }] = params;
                return `<b>${name}</b><br/>Count: <b>${value}</b>`;
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
