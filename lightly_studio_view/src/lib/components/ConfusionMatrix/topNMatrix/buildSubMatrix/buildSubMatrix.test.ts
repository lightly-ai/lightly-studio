import { describe, expect, it } from 'vitest';
import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL } from '../../types';
import { buildSubMatrix } from './buildSubMatrix';
import { OTHER_LABEL } from '../constants/constants';
import { small3Classes } from '../../fixtures';

const total = small3Classes.counts.flat().reduce((a, b) => a + b, 0);

describe('buildSubMatrix', () => {
    it('keeps visible classes, aggregates the rest into other, and preserves totals', () => {
        const sub = buildSubMatrix(small3Classes, ['person']);
        expect(sub.row_labels).toEqual(['person', OTHER_LABEL, NO_GROUND_TRUTH_ROW_LABEL]);
        expect(sub.col_labels).toEqual(['person', OTHER_LABEL, NO_PREDICTION_COL_LABEL]);
        expect(sub.counts.flat().reduce((a, b) => a + b, 0)).toBe(total);
        // person diagonal untouched
        expect(sub.counts[0][0]).toBe(156);
        // other/other aggregates bike+car block: 42+1+0+88
        expect(sub.counts[1][1]).toBe(131);
    });

    it('returns the empty matrix unchanged so the component empty-state is preserved', () => {
        const empty = { row_labels: [], col_labels: [], counts: [] };
        expect(buildSubMatrix(empty, [])).toBe(empty);
    });

    it('omits the other row/column when all classes are visible', () => {
        const sub = buildSubMatrix(small3Classes, ['bike', 'car', 'person']);
        expect(sub).toEqual(small3Classes);
    });

    it('routes a hidden real class named "(other)" into the aggregate bucket without collision', () => {
        // Dataset where one real annotation class is literally named '(other)'.
        const withOtherClass = {
            row_labels: ['bike', OTHER_LABEL, NO_GROUND_TRUTH_ROW_LABEL],
            col_labels: ['bike', OTHER_LABEL, NO_PREDICTION_COL_LABEL],
            counts: [
                [10, 2, 1],
                [3, 20, 4],
                [1, 2, 0]
            ]
        };
        const inputTotal = withOtherClass.counts.flat().reduce((a, b) => a + b, 0);

        // Hide the real '(other)' class; only 'bike' is visible.
        const sub = buildSubMatrix(withOtherClass, ['bike']);

        expect(sub.row_labels).toEqual(['bike', OTHER_LABEL, NO_GROUND_TRUTH_ROW_LABEL]);
        expect(sub.col_labels).toEqual(['bike', OTHER_LABEL, NO_PREDICTION_COL_LABEL]);
        // Grand total must be preserved.
        expect(sub.counts.flat().reduce((a, b) => a + b, 0)).toBe(inputTotal);
        // 'bike' diagonal is untouched.
        expect(sub.counts[0][0]).toBe(10);
        // The hidden real '(other)' class routes entirely into the aggregate row/col.
        expect(sub.counts[1]).toEqual([3, 20, 4]);
    });
});
