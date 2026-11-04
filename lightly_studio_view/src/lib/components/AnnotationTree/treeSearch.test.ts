import { describe, expect, it } from 'vitest';
import { buildMatcher, filterGroups, rowsInScope } from './treeSearch';
import { groupPairRows } from './groupPairRows';
import { buildPairRows } from './pairRows';

const SOURCES = [
    { id: 's1', name: 'ground_truth' },
    { id: 's2', name: 'model' }
];

const count = (collection: string, label: string, name: string) => ({
    annotation_collection_id: collection,
    annotation_label_id: label,
    label_name: name,
    current_count: 1,
    total_count: 1
});

const rows = buildPairRows(
    SOURCES,
    [count('s1', 'l1', 'car'), count('s1', 'l2', 'person'), count('s2', 'l1', 'car')],
    [],
    []
);

describe('buildMatcher', () => {
    it('returns null for an empty or whitespace query', () => {
        expect(buildMatcher('', false)).toBeNull();
        expect(buildMatcher('  ', true)).toBeNull();
    });

    it('matches a regex case-insensitively', () => {
        const matcher = buildMatcher('^ca', true)!;
        expect(matcher.invalid).toBe(false);
        expect(matcher.find('car')).toEqual({ start: 0, end: 2 });
        expect(matcher.find('scar')).toBeNull();
    });

    it('flags an invalid pattern and matches nothing', () => {
        const matcher = buildMatcher('(', true)!;
        expect(matcher.invalid).toBe(true);
        expect(matcher.find('(')).toBeNull();
    });

    it('matches a substring case-insensitively', () => {
        const matcher = buildMatcher('CA', false)!;
        expect(matcher.find('car')).toEqual({ start: 0, end: 2 });
        expect(matcher.find('scar')).toEqual({ start: 1, end: 3 });
        expect(matcher.find('dog')).toBeNull();
    });

    it('treats regex characters literally in substring mode', () => {
        expect(buildMatcher('(', false)!.find('a(b')).toEqual({ start: 1, end: 2 });
    });
});

describe('filterGroups', () => {
    const groups = groupPairRows(rows, 'source', SOURCES);

    it('keeps all rows of a group that matches by name', () => {
        const result = filterGroups(groups, buildMatcher('^ground', true)!.find);
        expect(result).toHaveLength(1);
        expect(result[0].rows).toHaveLength(2);
    });

    it('keeps only matching rows otherwise and drops empty groups', () => {
        const result = filterGroups(groups, buildMatcher('person', false)!.find);
        expect(result.map((group) => group.id)).toEqual(['s1']);
        expect(result[0].rows.map((row) => row.className)).toEqual(['person']);
    });
});

describe('rowsInScope', () => {
    it('returns the rows of all groups', () => {
        expect(rowsInScope(groupPairRows(rows, 'class', SOURCES))).toHaveLength(3);
    });

    it('excludes rows outside the search', () => {
        const groups = groupPairRows(rows, 'source', SOURCES);
        const scoped = rowsInScope(filterGroups(groups, buildMatcher('^ca', true)!.find));
        expect(scoped.map((row) => row.className)).toEqual(['car', 'car']);
    });
});
