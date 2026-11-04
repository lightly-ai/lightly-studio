import { describe, expect, it } from 'vitest';
import type { PairKey } from '$lib/components/AnnotationTree/pairRows';
import { buildTreeAnnotationsFilter } from './buildTreeAnnotationsFilter';

const pairA: PairKey = { collection_id: 'source-1', annotation_label_id: 'label-a' };
const pairB: PairKey = { collection_id: 'source-1', annotation_label_id: 'label-b' };
const pairC: PairKey = { collection_id: 'source-2', annotation_label_id: 'label-a' };
const allPairs = [pairA, pairB, pairC];
const sourceIds = ['source-1', 'source-2'];

describe('buildTreeAnnotationsFilter', () => {
    it('returns undefined when nothing is unticked', () => {
        expect(buildTreeAnnotationsFilter(allPairs, [], [], sourceIds)).toBeUndefined();
    });

    it('returns undefined when every unticked entry is stale', () => {
        const stalePair: PairKey = { collection_id: 'gone', annotation_label_id: 'label-x' };
        const result = buildTreeAnnotationsFilter(allPairs, [stalePair], ['gone'], sourceIds);
        expect(result).toBeUndefined();
    });

    it('gives every other pair and every source when one pair is unticked', () => {
        const result = buildTreeAnnotationsFilter(allPairs, [pairB], [], sourceIds);
        expect(result).toEqual({
            annotation_pairs: [pairA, pairC],
            unannotated_collection_ids: sourceIds
        });
    });

    it('gives [] pairs and the single ticked source when all pairs are unticked', () => {
        const result = buildTreeAnnotationsFilter(allPairs, allPairs, ['source-1'], sourceIds);
        expect(result).toEqual({
            annotation_pairs: [],
            unannotated_collection_ids: ['source-2']
        });
    });
});
