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

/** Bar layout: 'vertical' bars grow upward, 'horizontal' bars grow rightward. */
export type BarChartOrientation = 'vertical' | 'horizontal';

interface BuildEchartsOptionOptions {
    /**
     * Denominator for tooltip percentages. Pass the sum over all categories
     * when `data` is a subset (e.g. top-N), so percentages stay relative to
     * the full dataset. Defaults to the sum of `data`.
     */
    totalCount?: number;
    /** Bar orientation (default 'vertical'). */
    orientation?: BarChartOrientation;
}

export function buildEchartsOption(
    data: CategoryCount[],
    options: BuildEchartsOptionOptions = {}
): EChartsCoreOption {
    const totalCount = options.totalCount ?? data.reduce((sum, item) => sum + item.count, 0);
    const orientation = options.orientation ?? 'vertical';
    const isHorizontal = orientation === 'horizontal';

    const labels = data.map((item) => item.label);

    const categoryAxis = {
        type: 'category' as const,
        data: labels,
        axisLabel: {
            // Vertical layout rotates long labels so they don't overflow the
            // canvas edge (echarts containLabel ignores rotation); horizontal
            // layout has room for flat labels down the left gutter.
            rotate: isHorizontal ? 0 : 60,
            interval: 0,
            color: '#9ca3af',
            fontSize: 12,
            formatter: truncateLabel
        },
        axisLine: { lineStyle: { color: '#374151' } },
        axisTick: { alignWithLabel: true },
        // Keep the highest bar at the top when horizontal (data is pre-sorted).
        inverse: isHorizontal
    };

    const valueAxis = {
        type: 'value' as const,
        axisLabel: { color: '#9ca3af', fontSize: 12 },
        splitLine: { lineStyle: { color: '#374151' } }
    };

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
        xAxis: isHorizontal ? valueAxis : categoryAxis,
        yAxis: isHorizontal ? categoryAxis : valueAxis,
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
