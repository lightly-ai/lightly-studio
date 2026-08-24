import { describe, expect, it } from 'vitest';
import { calculateReviewAgreement, formatAgreement } from './reviewAgreement';

describe('calculateReviewAgreement', () => {
    const predictions = {
        positiveSampleIds: ['p1', 'p2'],
        negativeSampleIds: ['n1', 'n2']
    };

    it.each([
        ['unchanged predictions', new Set(['p1', 'p2']), 4],
        ['a corrected false positive', new Set(['p1']), 3],
        ['a corrected false negative', new Set(['p1', 'p2', 'n1']), 3],
        ['mixed corrections', new Set(['p1', 'n1']), 2]
    ])('%s', (_name, selectedSampleIds, expectedConfirmed) => {
        expect(calculateReviewAgreement(predictions, selectedSampleIds)).toEqual({
            confirmedPredictions: expectedConfirmed,
            reviewedSamples: 4
        });
    });

    it('uses the actual size of a smaller batch', () => {
        expect(
            calculateReviewAgreement(
                { positiveSampleIds: ['p1'], negativeSampleIds: ['n1'] },
                new Set(['p1'])
            )
        ).toEqual({ confirmedPredictions: 2, reviewedSamples: 2 });
    });
});

describe('formatAgreement', () => {
    it('formats a sample-weighted cumulative agreement', () => {
        expect(formatAgreement(34, 40)).toBe('85%');
        expect(formatAgreement(0, 0)).toBe('0%');
    });
});
