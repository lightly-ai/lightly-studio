import { describe, expect, it } from 'vitest';
import { groupPairRows } from './groupPairRows';
import { TEST_SOURCES, testRows } from './testRows';

const shape = (groups: ReturnType<typeof groupPairRows>, by: 'sourceName' | 'className') =>
    groups.map((group) => [group.name, group.rows.map((row) => row[by])]);

describe('groupPairRows', () => {
    const rows = testRows();

    it('groups the same pairs by source', () => {
        expect(shape(groupPairRows(rows, 'source', TEST_SOURCES), 'className')).toEqual([
            ['ground_truth', ['car', 'Deer']],
            ['model_v1.2', ['Deer', 'raccoon']]
        ]);
    });

    it('groups the same pairs by class', () => {
        expect(shape(groupPairRows(rows, 'class', TEST_SOURCES), 'sourceName')).toEqual([
            ['car', ['ground_truth']],
            ['Deer', ['ground_truth', 'model_v1.2']],
            ['raccoon', ['model_v1.2']]
        ]);
    });
});
