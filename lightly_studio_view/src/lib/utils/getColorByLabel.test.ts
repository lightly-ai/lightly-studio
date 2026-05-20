import { getColorByLabel } from './getColorByLabel';

describe('getColorByLabel', () => {
    // Test string input
    test('returns consistent colors for the same string', () => {
        const result1 = getColorByLabel('test');
        const result2 = getColorByLabel('test');
        expect(result1).toEqual(result2);
    });

    // Test different strings return different colors
    test('returns different colors for different strings', () => {
        const result1 = getColorByLabel('test1');
        const result2 = getColorByLabel('test2');
        expect(result1).not.toEqual(result2);
    });
});
