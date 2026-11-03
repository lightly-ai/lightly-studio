import { describe, expect, it } from 'vitest';
import { filterSourceTree, splitMatch } from './filterSourceTree';
import { buildSourceTree } from './buildSourceTree';

const count = (source: string, label: string) => ({
    annotation_collection_id: source,
    annotation_label_id: `${source}-${label}`,
    label_name: label,
    current_count: 1,
    total_count: 2
});

const tree = buildSourceTree(
    [
        { id: 'gt', name: 'ground_truth' },
        { id: 'model', name: 'model' }
    ],
    [count('gt', 'Deer'), count('gt', 'car'), count('model', 'raccoon')],
    []
);

describe('filterSourceTree', () => {
    it('returns the tree for an empty query', () => {
        expect(filterSourceTree(tree, '  ')).toBe(tree);
    });

    it('keeps matching classes case-insensitively and drops sources without a match', () => {
        const result = filterSourceTree(tree, 'DEE');
        expect(result.map((node) => node.name)).toEqual(['ground_truth']);
        expect(result[0].classes.map((item) => item.label)).toEqual(['Deer']);
        expect(result[0].count).toBe(tree[0].count);
    });

    it('returns nothing when no class matches', () => {
        expect(filterSourceTree(tree, 'zebra')).toEqual([]);
    });
});

describe('splitMatch', () => {
    it('splits around the first match', () => {
        expect(splitMatch('Raccoon', 'cco')).toEqual({ before: 'Ra', match: 'cco', after: 'on' });
        expect(splitMatch('Raccoon', 'x')).toEqual({ before: 'Raccoon', match: '', after: '' });
    });
});
