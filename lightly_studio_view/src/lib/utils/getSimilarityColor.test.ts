import { getSimilarityColor } from './getSimilarityColor';

describe('getSimilarityColor', () => {
    test('returns red for score 0', () => {
        expect(getSimilarityColor(0)).toBe('hsl(0, 80%, 50%)');
    });

    test('returns green for score 1', () => {
        expect(getSimilarityColor(1)).toBe('hsl(120, 80%, 50%)');
    });

    test('clamps scores outside [0, 1] range', () => {
        expect(getSimilarityColor(-0.5)).toBe('hsl(0, 80%, 50%)');
        expect(getSimilarityColor(1.5)).toBe('hsl(120, 80%, 50%)');
    });
});
