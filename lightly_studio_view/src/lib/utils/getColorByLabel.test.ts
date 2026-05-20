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

    test('returns different colors for different strings 1', () => {
        const result1 = getColorByLabel('afternoon');
        const result2 = getColorByLabel('night');
        expect(result1).not.toEqual(result2);
    });

    test('returns different colors for different strings 2', () => {
        const result1 = getColorByLabel('1');
        const result2 = getColorByLabel('1');
        expect(result1).toEqual(result2);
    });

    test('returns different colors for different strings 3', () => {
        const result1 = getColorByLabel('1-2');
        const result2 = getColorByLabel('1-2');
        expect(result1).toEqual(result2);
    });
});
