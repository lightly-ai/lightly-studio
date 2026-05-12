import { getColorPair } from './getColorPair';

describe('getColorPair', () => {
    test('formats color as rgba string', () => {
        expect(getColorPair({ r: 255, g: 0, b: 0 }, 1).color).toBe('rgba(255, 0, 0, 1)');
    });

    test('formats contrastColor as inverted rgba string', () => {
        expect(getColorPair({ r: 255, g: 0, b: 0 }, 1).contrastColor).toBe('rgba(0, 255, 255, 1)');
    });

    test('includes alpha in both outputs', () => {
        const { color, contrastColor } = getColorPair({ r: 100, g: 150, b: 200 }, 0.5);
        expect(color).toBe('rgba(100, 150, 200, 0.5)');
        expect(contrastColor).toBe('rgba(155, 105, 55, 0.5)');
    });
});
