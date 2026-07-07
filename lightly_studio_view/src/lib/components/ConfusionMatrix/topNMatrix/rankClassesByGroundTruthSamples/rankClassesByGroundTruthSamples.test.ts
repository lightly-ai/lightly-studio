import { describe, expect, it } from 'vitest';
import { rankClassesByGroundTruthSamples } from './rankClassesByGroundTruthSamples';
import { small3Classes } from '../../fixtures';

describe('rankClassesByGroundTruthSamples', () => {
    it('ranks classes by ground-truth row totals, descending', () => {
        // GT rows: bike=50, car=99, person=186
        expect(rankClassesByGroundTruthSamples(small3Classes)).toEqual(['person', 'car', 'bike']);
    });
});
