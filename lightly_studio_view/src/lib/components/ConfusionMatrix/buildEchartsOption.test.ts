import { describe, expect, it } from 'vitest';
import { buildEchartsOption } from './buildEchartsOption';
import { empty, singleClass, small3Classes } from './fixtures';
import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL, type ConfusionMatrix } from './types';

type Cell = [string, string, number, number];

function cell(col: string, row: string, count: number): Cell {
    return [col, row, count, Math.log10(count)];
}

interface VisualMap {
    seriesIndex: number;
    dimension: number;
    min: number;
    max: number;
    inRange: { color: [string, string] };
    show: boolean;
}

interface Series {
    name: string;
    data: Cell[];
}

interface Axis {
    data: string[];
}

interface BuiltOption {
    xAxis: Axis;
    yAxis: Axis;
    visualMap: VisualMap[];
    series: Series[];
    tooltip: { formatter: (params: { value: Cell }) => string };
}

function build(matrix: ConfusionMatrix): BuiltOption {
    return buildEchartsOption(matrix) as unknown as BuiltOption;
}

describe('buildEchartsOption', () => {
    it('uses col labels for xAxis and reversed row labels for yAxis', () => {
        const option = build(small3Classes);
        expect(option.xAxis.data).toEqual(['bike', 'car', 'person', NO_PREDICTION_COL_LABEL]);
        expect(option.yAxis.data).toEqual([NO_GROUND_TRUTH_ROW_LABEL, 'person', 'car', 'bike']);
    });

    it('places only real-class diagonal counts in the TP series', () => {
        const option = build(small3Classes);
        const tpSeries = option.series[0];
        expect(tpSeries.name).toBe('TP');
        // small3Classes diagonals for real classes: bike=42, car=88, person=156.
        // The sentinel/sentinel cell (FP-row, FN-col) is 0 and must be skipped.
        expect(new Set(tpSeries.data)).toEqual(
            new Set<Cell>([
                cell('bike', 'bike', 42),
                cell('car', 'car', 88),
                cell('person', 'person', 156)
            ])
        );
    });

    it('puts off-diagonal and sentinel-involving cells in the FP/FN series', () => {
        const option = build(small3Classes);
        const fpFnSeries = option.series[1];
        expect(fpFnSeries.name).toBe('FP/FN');

        // Should NOT contain any of the real-class diagonals.
        const diagonalPairs = new Set(['bike|bike', 'car|car', 'person|person']);
        for (const [col, row] of fpFnSeries.data) {
            expect(diagonalPairs.has(`${col}|${row}`)).toBe(false);
        }

        // Cells involving sentinel labels (FP row or FN column) must land here.
        const fpFnKeys = new Set(fpFnSeries.data.map(([c, r, n]) => `${c}|${r}|${n}`));
        expect(fpFnKeys.has(`${NO_PREDICTION_COL_LABEL}|bike|5`)).toBe(true);
        expect(fpFnKeys.has(`bike|${NO_GROUND_TRUTH_ROW_LABEL}|2`)).toBe(true);
    });

    it('skips cells whose count is zero or negative', () => {
        const matrix: ConfusionMatrix = {
            row_labels: ['a', 'b'],
            col_labels: ['a', 'b'],
            counts: [
                [5, 0],
                [-1, 7]
            ]
        };
        const option = build(matrix);
        const allCells = [...option.series[0].data, ...option.series[1].data];
        expect(allCells).toHaveLength(2);
        expect(allCells.map(([, , n]) => n).sort()).toEqual([5, 7]);
    });

    it('does not treat sentinel/sentinel cells as TP even when row label equals col label', () => {
        // Force a same-named sentinel row and col to exercise the SENTINEL_LABELS guard.
        const matrix: ConfusionMatrix = {
            row_labels: [NO_GROUND_TRUTH_ROW_LABEL],
            col_labels: [NO_GROUND_TRUTH_ROW_LABEL],
            counts: [[9]]
        };
        const option = build(matrix);
        expect(option.series[0].data).toEqual([]);
        expect(option.series[1].data).toEqual([
            cell(NO_GROUND_TRUTH_ROW_LABEL, NO_GROUND_TRUTH_ROW_LABEL, 9)
        ]);
    });

    it('maps color from the log dimension with a shared log-scaled range', () => {
        const option = build(small3Classes);
        const [tpMap, fpFnMap] = option.visualMap;
        // small3Classes' largest cell is 156 (person→person).
        expect(tpMap.dimension).toBe(3);
        expect(tpMap.min).toBe(0);
        expect(tpMap.max).toBe(Math.log10(156));
        expect(fpFnMap.dimension).toBe(3);
        expect(fpFnMap.min).toBe(0);
        expect(fpFnMap.max).toBe(Math.log10(156));
        expect(tpMap.seriesIndex).toBe(0);
        expect(fpFnMap.seriesIndex).toBe(1);
    });

    it('divides the visualMap range by colorIntensity so cells saturate earlier', () => {
        const option = buildEchartsOption(small3Classes, {
            colorIntensity: 2
        }) as unknown as BuiltOption;
        expect(option.visualMap[0].max).toBe(Math.log10(156) / 2);
        expect(option.visualMap[1].max).toBe(Math.log10(156) / 2);
    });

    it('keeps max at 1 when every cell is empty so visualMap stays valid', () => {
        const option = build(empty);
        expect(option.visualMap[0].max).toBe(1);
        expect(option.visualMap[1].max).toBe(1);
        expect(option.series[0].data).toEqual([]);
        expect(option.series[1].data).toEqual([]);
    });

    it('handles the single-class fixture: one TP cell plus sentinel-involving FP/FN cells', () => {
        const option = build(singleClass);
        expect(option.series[0].data).toEqual([cell('person', 'person', 142)]);
        expect(new Set(option.series[1].data)).toEqual(
            new Set<Cell>([
                cell(NO_PREDICTION_COL_LABEL, 'person', 18),
                cell('person', NO_GROUND_TRUTH_ROW_LABEL, 11)
            ])
        );
    });

    it('renders a tooltip with GT, Pred, and Count from the cell value', () => {
        const option = build(small3Classes);
        const html = option.tooltip.formatter({ value: cell('car', 'bike', 3) });
        expect(html).toContain('GT: <b>bike</b>');
        expect(html).toContain('Pred: <b>car</b>');
        expect(html).toContain('Count: <b>3</b>');
    });
});
