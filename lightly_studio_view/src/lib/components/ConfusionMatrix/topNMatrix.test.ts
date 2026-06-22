import { describe, expect, it } from 'vitest';
import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL } from './types';
import {
    buildSubMatrix,
    getRealClasses,
    OTHER_LABEL,
    rankClasses,
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

describe('rankClasses', () => {
    it('most-confused matches rankClassesByConfusion and least-confused reverses it', () => {
        expect(rankClasses(fixture, 'most-confused')).toEqual(['person', 'car', 'bike']);
        expect(rankClasses(fixture, 'least-confused')).toEqual(['bike', 'car', 'person']);
    });

    it('most-samples ranks by ground-truth row totals', () => {
        // GT rows: bike=50, car=99, person=186
        expect(rankClasses(fixture, 'most-samples')).toEqual(['person', 'car', 'bike']);
    });

    it('alphabetical sorts labels without mutating the source order', () => {
        expect(rankClasses(fixture, 'alphabetical')).toEqual(['bike', 'car', 'person']);
        expect(getRealClasses(fixture)).toEqual(['bike', 'car', 'person']);
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
