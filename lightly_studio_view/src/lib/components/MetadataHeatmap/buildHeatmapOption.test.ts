import { describe, expect, it } from 'vitest';
import { buildHeatmapOption, isCellSelected } from './buildHeatmapOption';

interface HeatmapSeriesOption {
    name: string;
    data: [number, number, number, number][];
    label: { show: boolean };
}

const xAxis = { name: 'month', labels: ['April', 'March'] };
const yAxis = { name: 'year', labels: ['2025', '2026'] };
// counts[y][x]: April 2025 = 10, March 2025 = 1, April 2026 = 0, March 2026 = 4.
const counts = [
    [10, 1],
    [0, 4]
];

const build = (selection: Parameters<typeof buildHeatmapOption>[0]['selection']) =>
    buildHeatmapOption({ xAxis, yAxis, counts, selection, valueNoun: 'samples' }) as {
        series: HeatmapSeriesOption[];
        yAxis: { inverse: boolean; data: string[] };
        tooltip: { formatter: (params: { value: [number, number, number, number] }) => string };
    };

describe('buildHeatmapOption', () => {
    it('puts every non-empty cell in the selected series when nothing is selected', () => {
        const [selected, dimmed] = build(null).series;

        expect(selected.data).toEqual([
            [0, 0, 10, 1],
            [1, 0, 1, 0],
            [1, 1, 4, Math.log10(4)]
        ]);
        expect(dimmed.data).toEqual([]);
    });

    it('dims the cells outside the selection', () => {
        const [selected, dimmed] = build({ x: [0], y: null }).series;

        expect(selected.data.map(([x, y]) => [x, y])).toEqual([[0, 0]]);
        expect(dimmed.data.map(([x, y]) => [x, y])).toEqual([
            [1, 0],
            [1, 1]
        ]);
    });

    it('keeps the first y bucket at the top and labels small grids', () => {
        const option = build(null);

        expect(option.yAxis).toMatchObject({ inverse: true, data: ['2025', '2026'] });
        expect(option.series[0].label.show).toBe(true);
    });

    it('escapes the metadata values in the tooltip', () => {
        const option = buildHeatmapOption({
            xAxis: { name: 'city', labels: ['<b>Zurich</b>'] },
            yAxis: { name: 'year', labels: ['2025'] },
            counts: [[2]],
            selection: null,
            valueNoun: 'samples'
        }) as ReturnType<typeof build>;

        expect(option.tooltip.formatter({ value: [0, 0, 2, Math.log10(2)] })).toBe(
            'city: <b>&lt;b&gt;Zurich&lt;/b&gt;</b><br/>year: <b>2025</b><br/>2 samples'
        );
    });
});

describe('isCellSelected', () => {
    it('selects a cell only when the buckets of both axes are selected', () => {
        const selection = { x: [1], y: [0, 2] };

        expect(isCellSelected(selection, 1, 2)).toBe(true);
        expect(isCellSelected(selection, 0, 2)).toBe(false);
        expect(isCellSelected(selection, 1, 1)).toBe(false);
        expect(isCellSelected({ x: null, y: [0] }, 5, 0)).toBe(true);
        expect(isCellSelected(null, 5, 5)).toBe(true);
    });
});
