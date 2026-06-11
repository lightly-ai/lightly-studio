import { describe, expect, it } from 'vitest';
import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL } from '../types';
import {
    buildSubMatrix,
    filterClasses,
    getRealClasses,
    OTHER_LABEL,
    rankClassesByConfusion
} from './topNMatrix';

const fixture = {
    row_labels: ['bike', 'car', 'person', NO_GROUND_TRUTH_ROW_LABEL],
    col_labels: ['bike', 'car', 'person', NO_PREDICTION_COL_LABEL],
    counts: [
        [42, 1, 2, 5],
        [0, 88, 4, 7],
        [3, 6, 156, 21],
        [2, 4, 8, 0]
    ]
};

const total = fixture.counts.flat().reduce((a, b) => a + b, 0);

describe('getRealClasses', () => {
    it('excludes sentinel labels', () => {
        expect(getRealClasses(fixture)).toEqual(['bike', 'car', 'person']);
    });
});

describe('rankClassesByConfusion', () => {
    it('ranks classes by off-diagonal involvement', () => {
        // person: row(3+6+21) + col(2+4+8) = 44; car: row(0+4+7) + col(1+6+4) = 22;
        // bike: row(1+2+5) + col(0+3+2) = 13
        expect(rankClassesByConfusion(fixture)).toEqual(['person', 'car', 'bike']);
    });
});

describe('filterClasses', () => {
    const classes = ['bike', 'car', 'person', 'traffic light'];

    it('matches a single term as case-insensitive substring', () => {
        expect(filterClasses(classes, 'CAR')).toEqual(['car']);
        expect(filterClasses(classes, 'i')).toEqual(['bike', 'traffic light']);
    });

    it('OR-combines comma-separated terms', () => {
        expect(filterClasses(classes, 'car, bike')).toEqual(['bike', 'car']);
        expect(filterClasses(classes, 'person,traffic')).toEqual(['person', 'traffic light']);
    });

    it('ignores empty terms and returns all classes for a blank query', () => {
        expect(filterClasses(classes, '')).toEqual(classes);
        expect(filterClasses(classes, ' , ,')).toEqual(classes);
        expect(filterClasses(classes, 'car, ,')).toEqual(['car']);
    });
});

describe('buildSubMatrix', () => {
    it('keeps visible classes, aggregates the rest into other, and preserves totals', () => {
        const sub = buildSubMatrix(fixture, ['person']);
        expect(sub.row_labels).toEqual(['person', OTHER_LABEL, NO_GROUND_TRUTH_ROW_LABEL]);
        expect(sub.col_labels).toEqual(['person', OTHER_LABEL, NO_PREDICTION_COL_LABEL]);
        expect(sub.counts.flat().reduce((a, b) => a + b, 0)).toBe(total);
        // person diagonal untouched
        expect(sub.counts[0][0]).toBe(156);
        // other/other aggregates bike+car block: 42+1+0+88
        expect(sub.counts[1][1]).toBe(131);
    });

    it('omits the other row/column when all classes are visible', () => {
        const sub = buildSubMatrix(fixture, ['bike', 'car', 'person']);
        expect(sub).toEqual(fixture);
    });
});
