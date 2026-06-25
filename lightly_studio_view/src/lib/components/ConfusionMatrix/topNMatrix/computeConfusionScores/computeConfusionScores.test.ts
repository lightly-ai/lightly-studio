import { describe, expect, it } from 'vitest';
import { computeConfusionScores } from './computeConfusionScores';
import { small3Classes } from '../../fixtures';

describe('computeConfusionScores', () => {
    it('sums off-diagonal mass per real class (as ground truth and prediction)', () => {
        // person: row(3+6+21) + col(2+4+8) = 44; car: row(4+7) + col(1+6+4) = 22;
        // bike: row(1+2+5) + col(3+2) = 13
        const scores = computeConfusionScores(small3Classes);
        expect(scores.get('person')).toBe(44);
        expect(scores.get('car')).toBe(22);
        expect(scores.get('bike')).toBe(13);
    });
});
