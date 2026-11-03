import { describe, expect, it } from 'vitest';
import { createMatcher, matchRows, splitAtRange } from './treeSearch';
import { testRows } from './testRows';

const names = (rows: ReturnType<typeof testRows>) =>
    rows.map((row) => `${row.sourceName}/${row.className}`);

describe('treeSearch', () => {
    const rows = testRows();

    it('matches a substring of the class name, case-insensitively', () => {
        expect(names(matchRows(rows, createMatcher('dEE', false)))).toEqual([
            'ground_truth/Deer',
            'model_v1.2/Deer'
        ]);
    });

    it('keeps every class of a source whose name matches', () => {
        expect(names(matchRows(rows, createMatcher('ground', false)))).toEqual([
            'ground_truth/car',
            'ground_truth/Deer'
        ]);
    });

    it('matches a dot literally without regex and as any character with regex', () => {
        expect(matchRows(rows, createMatcher('v1x2', false))).toEqual([]);
        expect(names(matchRows(rows, createMatcher('v1.2', false)))).toHaveLength(2);
        expect(names(matchRows(rows, createMatcher('^(car|rac)', true)))).toEqual([
            'ground_truth/car',
            'model_v1.2/raccoon'
        ]);
    });

    it('reports an invalid pattern and keeps every row', () => {
        const matcher = createMatcher('(', true);
        expect(matcher.kind).toBe('invalid');
        expect(matchRows(rows, matcher)).toBe(rows);
    });

    it('finds the first match range for highlighting', () => {
        const matcher = createMatcher('c+o', true);
        const range = matcher.kind === 'ok' ? matcher.find('raccoon') : null;
        expect(splitAtRange('raccoon', range)).toEqual({ before: 'ra', match: 'cco', after: 'on' });
    });
});
