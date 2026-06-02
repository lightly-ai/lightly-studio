import {
    hexToRgb,
    hexToRgba,
    rgbaToHex,
    rgbaFromBytes,
    withAlpha,
    stripAlpha
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
