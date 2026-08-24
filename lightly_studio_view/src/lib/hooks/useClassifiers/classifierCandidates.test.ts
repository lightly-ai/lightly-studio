import { describe, expect, it } from 'vitest';
import { mergeClassifierCandidates } from './classifierCandidates';

const sample = (sampleId: string) => ({ sample_id: sampleId });

describe('mergeClassifierCandidates', () => {
    it('places preferred samples first and removes duplicates', () => {
        expect(
            mergeClassifierCandidates(
                [sample('selected-1'), sample('selected-2')],
                [sample('selected-1'), sample('other-1')],
                3
            )
        ).toEqual([sample('selected-1'), sample('selected-2'), sample('other-1')]);
    });

    it('caps the candidate set', () => {
        const samples = Array.from({ length: 25 }, (_, index) => sample(String(index)));
        expect(mergeClassifierCandidates([], samples)).toHaveLength(20);
    });

    it('returns every available sample when the collection is smaller than the limit', () => {
        expect(mergeClassifierCandidates([], [sample('1'), sample('2')])).toHaveLength(2);
    });
});
