import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { getColorByLabel } from './getColorByLabel';

afterEach(() => {
    useCustomLabelColors().clearCustomColors();
});

describe('getColorByLabel', () => {
    test('returns consistent colors for the same string', () => {
        const result1 = getColorByLabel('test');
        const result2 = getColorByLabel('test');
        expect(result1).toEqual(result2);
    });

    test('returns different colors for different strings', () => {
        const result1 = getColorByLabel('test1');
        const result2 = getColorByLabel('test2');
        expect(result1).not.toEqual(result2);
    });

    test('returns an rgba color and an RGB-inverted contrast color', () => {
        expect(getColorByLabel('cat')).toEqual({
            color: 'rgba(0, 0, 255, 1)',
            contrastColor: 'rgba(255, 255, 0, 1)'
        });
    });

    test('clamps alpha below 0 to 0 and above 1 to 1', () => {
        expect(getColorByLabel('test', -5).color).toContain(', 0)');
        expect(getColorByLabel('test', 2).color).toContain(', 1)');
    });

    describe('with a custom color override', () => {
        test('uses the override hex with an RGB-inverted contrast, mixing the override alpha with the requested alpha', () => {
            useCustomLabelColors().setCustomColor('cat', '#ff8040', 0.8);
            expect(getColorByLabel('cat', 0.5).color).toBe('rgba(255, 128, 64, 0.4)');

            useCustomLabelColors().setCustomColor('cat', '#ff8040', 1);
            const { color, contrastColor } = getColorByLabel('cat', 1);
            expect(color).toBe('rgba(255, 128, 64, 1)');
            expect(contrastColor).toBe('rgba(0, 127, 191, 1)');
        });

        test('falls back to the palette color once the override is cleared', () => {
            const original = getColorByLabel('cat', 1);

            useCustomLabelColors().setCustomColor('cat', '#ff8040', 1);
            expect(getColorByLabel('cat', 1)).not.toEqual(original);

            useCustomLabelColors().deleteCustomColor('cat');
            expect(getColorByLabel('cat', 1)).toEqual(original);
        });
    });
});
