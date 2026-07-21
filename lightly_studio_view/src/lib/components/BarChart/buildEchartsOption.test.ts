import { describe, expect, it } from 'vitest';
import { buildEchartsOption, unionCategories } from './buildEchartsOption';
import { balanced } from './fixtures';
import type { ChartSeries } from './types';

/** Wrap a single count array into the unlabelled series BarChart builds. */
const single = (data = balanced): ChartSeries[] => [{ id: 'default', label: '', data }];

describe('buildEchartsOption', () => {
    it('maps labels to the category axis and counts to the bar series', () => {
        const option = buildEchartsOption(single()) as {
            xAxis: { data: string[] };
            series: [{ type: string; data: number[] }];
        };

        expect(option.xAxis.data).toEqual(balanced.map((item) => item.label));
        expect(option.series[0].type).toBe('bar');
        expect(option.series[0].data).toEqual(balanced.map((item) => item.count));
    });

    it('puts categories on the value axis when horizontal, keeping the bar series', () => {
        const option = buildEchartsOption(single(), { orientation: 'horizontal' }) as {
            xAxis: { type: string };
            yAxis: { type: string; data: string[]; inverse: boolean };
            series: [{ type: string; data: number[] }];
        };

        expect(option.xAxis.type).toBe('value');
        expect(option.yAxis.type).toBe('category');
        expect(option.yAxis.data).toEqual(balanced.map((item) => item.label));
        // Highest bar (first, pre-sorted) stays at the top.
        expect(option.yAxis.inverse).toBe(true);
        expect(option.series[0].data).toEqual(balanced.map((item) => item.count));
    });

    const getFormatter = (option: unknown) =>
        (
            option as {
                tooltip: {
                    formatter: (
                        params: {
                            name: string;
                            value: number;
                            seriesName?: string;
                            marker?: string;
                            seriesIndex?: number;
                            dataIndex?: number;
                        }[]
                    ) => string;
                };
            }
        ).tooltip.formatter;

    it('shows the percentage of the data sum in the tooltip', () => {
        const formatter = getFormatter(
            buildEchartsOption(
                single([
                    { label: 'car', count: 25 },
                    { label: 'dog', count: 75 }
                ])
            )
        );

        expect(formatter([{ name: 'car', value: 25 }])).toBe(
            '<b>car</b><br/>Count: <b>25</b> (25.0%)'
        );
    });

    it('uses the provided totalCount as the percentage denominator', () => {
        const formatter = getFormatter(
            buildEchartsOption(single([{ label: 'car', count: 25 }]), { totalCount: 1000 })
        );

        expect(formatter([{ name: 'car', value: 25 }])).toBe(
            '<b>car</b><br/>Count: <b>25</b> (2.5%)'
        );
    });

    it('renders tiny shares as <0.1% and omits percentages for an empty total', () => {
        const small = getFormatter(
            buildEchartsOption(single([{ label: 'car', count: 1 }]), { totalCount: 10000 })
        );
        expect(small([{ name: 'car', value: 1 }])).toBe('<b>car</b><br/>Count: <b>1</b> (<0.1%)');

        const empty = getFormatter(buildEchartsOption(single([])));
        expect(empty([{ name: 'car', value: 0 }])).toBe('<b>car</b><br/>Count: <b>0</b>');
    });

    describe('scale', () => {
        it('uses a linear value axis by default', () => {
            const option = buildEchartsOption(single()) as { yAxis: { type: string } };
            expect(option.yAxis.type).toBe('value');
        });

        it('switches the value axis to log scale on the value axis only', () => {
            const option = buildEchartsOption(single(), { scale: 'log' }) as {
                yAxis: { type: string };
                xAxis: { type: string };
            };
            // Category axis stays categorical; only the value axis becomes log.
            expect(option.yAxis.type).toBe('log');
            expect(option.xAxis.type).toBe('category');
        });

        it('keeps the log scale on the value axis when horizontal', () => {
            const option = buildEchartsOption(single(), {
                scale: 'log',
                orientation: 'horizontal'
            }) as { xAxis: { type: string }; yAxis: { type: string } };
            expect(option.xAxis.type).toBe('log');
            expect(option.yAxis.type).toBe('category');
        });
    });

    describe('multi-series comparison', () => {
        const seriesA: ChartSeries = {
            id: 'a',
            label: 'Tag A',
            data: [
                { label: 'sunny', count: 30 },
                { label: 'rainy', count: 10 }
            ]
        };
        const seriesB: ChartSeries = {
            id: 'b',
            label: 'Tag B',
            data: [
                { label: 'sunny', count: 20 },
                { label: 'cloudy', count: 20 }
            ]
        };

        it('renders one bar series per input, aligned to the union of categories', () => {
            const option = buildEchartsOption([seriesA, seriesB]) as {
                xAxis: { data: string[] };
                series: { name: string; type: string; data: number[] }[];
            };

            // Union: seriesA order first, then labels unique to seriesB.
            expect(option.xAxis.data).toEqual(['sunny', 'rainy', 'cloudy']);
            expect(option.series).toHaveLength(2);
            expect(option.series[0].name).toBe('Tag A');
            // Missing categories fill with 0 (rainy absent from B, cloudy from A).
            expect(option.series[0].data).toEqual([30, 10, 0]);
            expect(option.series[1].data).toEqual([20, 0, 20]);
        });

        it('adds a legend only when more than one series is present', () => {
            const multi = buildEchartsOption([seriesA, seriesB]) as { legend?: { data: string[] } };
            expect(multi.legend?.data).toEqual(['Tag A', 'Tag B']);

            const solo = buildEchartsOption(single()) as { legend?: unknown };
            expect(solo.legend).toBeUndefined();
        });

        it('normalizes within each series to a percentage', () => {
            const option = buildEchartsOption([seriesA, seriesB], {
                normalize: 'percentage'
            }) as { series: { data: number[] }[] };

            // Series A total 40 → sunny 75%, rainy 25%; series B total 40 → sunny/cloudy 50%.
            expect(option.series[0].data).toEqual([75, 25, 0]);
            expect(option.series[1].data).toEqual([50, 0, 50]);
        });

        it('formats percentage tooltips per series', () => {
            const formatter = getFormatter(
                buildEchartsOption([seriesA, seriesB], { normalize: 'percentage' })
            );
            const text = formatter([
                { name: 'sunny', value: 75, seriesName: 'Tag A', marker: 'A' },
                { name: 'sunny', value: 50, seriesName: 'Tag B', marker: 'B' }
            ]);
            expect(text).toBe('<b>sunny</b><br/>ATag A: <b>75.0%</b><br/>BTag B: <b>50.0%</b>');
        });
    });

    describe('histogram mode', () => {
        const bins = [
            { label: '0–1', count: 5 },
            { label: '1–2', count: 8 },
            { label: '(none)', count: 2 }
        ];

        it('keeps a single numeric series as touching bars', () => {
            const option = buildEchartsOption(single(bins), { mode: 'histogram' }) as {
                series: { type: string; barCategoryGap: string }[];
            };
            expect(option.series[0].type).toBe('bar');
            expect(option.series[0].barCategoryGap).toBe('0%');
        });

        it('renders step-line density curves when comparing several series', () => {
            const option = buildEchartsOption(
                [
                    { id: 'a', label: 'A', data: bins },
                    { id: 'b', label: 'B', data: bins }
                ],
                { mode: 'histogram' }
            ) as { series: { type: string; step?: string }[] };
            expect(option.series[0].type).toBe('line');
            expect(option.series[0].step).toBe('middle');
        });

        it('keeps zero-count values on linear multi-series curves', () => {
            const option = buildEchartsOption(
                [
                    { id: 'a', label: 'A', data: [{ label: '0–1', count: 5 }] },
                    { id: 'b', label: 'B', data: [{ label: '1–2', count: 8 }] }
                ],
                { mode: 'histogram' }
            ) as { series: { data: number[] }[] };
            // Linear scale renders zeros at the baseline, keeping the curve continuous.
            expect(option.series[0].data).toEqual([5, 0]);
        });

        it('floors zero-count bins to the log floor so the curve dips instead of breaking', () => {
            const option = buildEchartsOption(
                [
                    { id: 'a', label: 'A', data: [{ label: '0–1', count: 5 }] },
                    { id: 'b', label: 'B', data: [{ label: '1–2', count: 8 }] }
                ],
                { mode: 'histogram', scale: 'log' }
            ) as { series: { data: number[] }[]; yAxis: { min?: number } };
            // Smallest real value is 5 → floor one decade below its decade = 0.1.
            // Zero bins take the floor (no null, no bridge) and the axis pins to it.
            expect(option.series[0].data).toEqual([5, 0.1]);
            expect(option.yAxis.min).toBe(0.1);
        });

        it('reports the true value for log-floored bins in the tooltip', () => {
            const option = buildEchartsOption(
                [
                    { id: 'a', label: 'A', data: [{ label: '0–1', count: 5 }] },
                    { id: 'b', label: 'B', data: [{ label: '1–2', count: 8 }] }
                ],
                { mode: 'histogram', scale: 'log' }
            );
            const formatter = getFormatter(option);
            // dataIndex 1 for series A is the floored zero bin; tooltip shows 0, not 0.1.
            const text = formatter([
                {
                    name: '1–2',
                    value: 0.1,
                    seriesName: 'A',
                    marker: 'X',
                    seriesIndex: 0,
                    dataIndex: 1
                }
            ]);
            expect(text).toBe('<b>1–2</b><br/>XA: <b>0</b>');
        });
    });

    describe('mean marker', () => {
        const withMean: ChartSeries[] = [
            {
                id: 'a',
                label: '',
                mean: { value: 0.4231, categoryIndex: 1.25 },
                data: [
                    { label: '0–1', count: 5 },
                    { label: '1–2', count: 8 }
                ]
            }
        ];

        it('adds a dashed markLine at the mean category index on the value-carrying axis', () => {
            const vertical = buildEchartsOption(withMean, { mode: 'histogram' }) as {
                series: [{ markLine?: { lineStyle: { type: string }; data: { xAxis: number }[] } }];
            };
            expect(vertical.series[0].markLine?.lineStyle.type).toBe('dashed');
            expect(vertical.series[0].markLine?.data).toEqual([{ xAxis: 1.25 }]);

            const horizontal = buildEchartsOption(withMean, {
                mode: 'histogram',
                orientation: 'horizontal'
            }) as { series: [{ markLine?: { data: { yAxis: number }[] } }] };
            expect(horizontal.series[0].markLine?.data).toEqual([{ yAxis: 1.25 }]);
        });

        it('labels the marker with a trimmed mean value', () => {
            const option = buildEchartsOption(withMean, { mode: 'histogram' }) as {
                series: [{ markLine?: { label: { formatter: string } } }];
            };
            expect(option.series[0].markLine?.label.formatter).toBe('μ 0.42');
        });

        it('omits the markLine for series without a mean', () => {
            const option = buildEchartsOption(single(), { mode: 'histogram' }) as {
                series: [{ markLine?: unknown }];
            };
            expect(option.series[0].markLine).toBeUndefined();
        });
    });

    describe('unionCategories', () => {
        it('pins the (none) bucket last', () => {
            const categories = unionCategories([
                {
                    id: 'a',
                    label: '',
                    data: [
                        { label: '(none)', count: 1 },
                        { label: 'x', count: 2 },
                        { label: 'y', count: 3 }
                    ]
                }
            ]);
            expect(categories).toEqual(['x', 'y', '(none)']);
        });
    });
});
