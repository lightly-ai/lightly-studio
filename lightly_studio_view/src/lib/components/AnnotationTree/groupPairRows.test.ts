import { describe, expect, it } from 'vitest';
import { groupPairRows } from './groupPairRows';
import { buildPairRows } from './pairRows';

const SOURCES = [
    { id: 's1', name: 'ground_truth' },
    { id: 's2', name: 'model' },
    { id: 's3', name: 'empty' }
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
    [count('s1', 'l1', 'car'), count('s2', 'l2', 'car'), count('s2', 'l3', 'bike')],
    [],
    []
);

describe('groupPairRows', () => {
    it('keeps a source without counts as an empty group when grouping by source', () => {
        const groups = groupPairRows(rows, 'source', SOURCES);

        expect(groups.map((group) => [group.name, group.rows.length])).toEqual([
            ['ground_truth', 1],
            ['model', 2],
            ['empty', 0]
        ]);
        expect(groups[2]).toMatchObject({ sourceId: 's3', rows: [] });
    });

    it('merges a class of two sources into one group when grouping by class', () => {
        const groups = groupPairRows(rows, 'class', SOURCES);

        expect(groups.map((group) => group.name)).toEqual(['bike', 'car']);
        expect(groups[1].rows.map((row) => row.sourceName)).toEqual(['ground_truth', 'model']);
        expect(groups[1].sourceId).toBeUndefined();
    });
});
