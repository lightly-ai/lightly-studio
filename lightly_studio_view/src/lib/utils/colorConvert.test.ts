import {
    hexToRgb,
    hexToRgba,
    rgbaToHex,
    rgbaFromBytes,
    withAlpha,
    stripAlpha,
    oklchToRgb,
    oklchHueWheelColor
} from './colorConvert';

describe('hexToRgb', () => {
    test('parses a six-digit hex', () => {
        expect(hexToRgb('#ff8040')).toEqual({ r: 255, g: 128, b: 64 });
    });

    test('parses pure black and white', () => {
        expect(hexToRgb('#000000')).toEqual({ r: 0, g: 0, b: 0 });
        expect(hexToRgb('#ffffff')).toEqual({ r: 255, g: 255, b: 255 });
    });
});

describe('hexToRgba', () => {
    test('combines hex with the given alpha', () => {
        expect(hexToRgba('#ff8040', 0.5)).toBe('rgba(255, 128, 64, 0.5)');
    });
});

describe('rgbaToHex', () => {
    test('converts an rgba string to hex', () => {
        expect(rgbaToHex('rgba(255, 128, 64, 0.5)')).toBe('#ff8040');
    });

    test('also accepts the rgb(...) form', () => {
        expect(rgbaToHex('rgb(255, 128, 64)')).toBe('#ff8040');
    });

    test('returns undefined when the input does not match an rgb(a) pattern', () => {
        expect(rgbaToHex('not-a-color')).toBeUndefined();
        expect(rgbaToHex('#ff0000')).toBeUndefined();
    });
});

describe('rgbaFromBytes', () => {
    test('scales the 0-255 alpha byte into 0-1', () => {
        expect(rgbaFromBytes([10, 20, 30, 255])).toBe('rgba(10, 20, 30, 1)');
        expect(rgbaFromBytes([10, 20, 30, 0])).toBe('rgba(10, 20, 30, 0)');
    });

    test('handles fractional alpha', () => {
        expect(rgbaFromBytes([10, 20, 30, 128])).toBe(`rgba(10, 20, 30, ${128 / 255})`);
    });
});

describe('withAlpha', () => {
    test('replaces alpha in an rgba string', () => {
        expect(withAlpha('rgba(10, 20, 30, 0.4)', 0.9)).toBe('rgba(10, 20, 30, 0.9)');
    });

    test('promotes rgb to rgba with the supplied alpha', () => {
        expect(withAlpha('rgb(10, 20, 30)', 0.25)).toBe('rgba(10, 20, 30, 0.25)');
    });

    test('returns input unchanged when no rgb(a) match is found', () => {
        expect(withAlpha('hsl(0, 100%, 50%)', 0.5)).toBe('hsl(0, 100%, 50%)');
    });
});

describe('oklchToRgb', () => {
    test('maps achromatic OKLCH to neutral sRGB', () => {
        // Zero chroma at full lightness is white; at zero lightness, black.
        expect(oklchToRgb(1, 0, 0)).toEqual({ r: 255, g: 255, b: 255 });
        expect(oklchToRgb(0, 0, 0)).toEqual({ r: 0, g: 0, b: 0 });
    });

    test('produces an in-gamut hue at the palette lightness/chroma', () => {
        // Hue 120° at L=0.8, C=0.22 is a yellow-green inside the sRGB gamut.
        expect(oklchToRgb(0.8, 0.22, 120)).toEqual({ r: 173, g: 208, b: 0 });
    });

    test('clamps out-of-gamut channels to the 0-255 range', () => {
        const { r, g, b } = oklchToRgb(0.8, 0.22, 0);
        for (const channel of [r, g, b]) {
            expect(channel).toBeGreaterThanOrEqual(0);
            expect(channel).toBeLessThanOrEqual(255);
        }
    });
});

describe('oklchHueWheelColor', () => {
    test('places index 0 at the start of the hue circle', () => {
        // Same as oklchToRgb at hue 0 for the given lightness/chroma.
        expect(oklchHueWheelColor({ index: 0, count: 4, lightness: 0.65, chroma: 0.3 })).toEqual(
            oklchToRgb(0.65, 0.3, 0)
        );
    });

    test('spreads hues evenly: index i sits at i/count around the circle', () => {
        // index 1 of 4 → hue 90°.
        expect(oklchHueWheelColor({ index: 1, count: 4, lightness: 0.65, chroma: 0.3 })).toEqual(
            oklchToRgb(0.65, 0.3, 90)
        );
    });

    test('hueOffset rotates the wheel and wraps past 360°', () => {
        // index 3 of 4 → 270°, +120° offset → 390° wraps to 30°.
        expect(
            oklchHueWheelColor({ index: 3, count: 4, lightness: 0.65, chroma: 0.3, hueOffset: 120 })
        ).toEqual(oklchToRgb(0.65, 0.3, 30));
    });
});

describe('stripAlpha', () => {
    test('drops the alpha channel from an rgba string', () => {
        expect(stripAlpha('rgba(10, 20, 30, 0.4)')).toBe('rgb(10, 20, 30)');
    });

    test('leaves an rgb string untouched', () => {
        expect(stripAlpha('rgb(10, 20, 30)')).toBe('rgb(10, 20, 30)');
    });

    test('returns input unchanged when no rgb(a) match is found', () => {
        expect(stripAlpha('hsl(0, 100%, 50%)')).toBe('hsl(0, 100%, 50%)');
    });
});
