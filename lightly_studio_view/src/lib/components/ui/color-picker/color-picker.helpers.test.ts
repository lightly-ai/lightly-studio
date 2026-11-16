import { describe, expect, it } from 'vitest';
import { hexToHsl, hslToHex, isHexColor } from './color-picker.helpers';

describe('color-picker helpers', () => {
    it.each([
        ['#ff0000', { h: 0, s: 100, l: 50 }],
        ['#ff8080', { h: 0, s: 100, l: 75 }],
        ['#888888', { h: 0, s: 0, l: 53 }],
        ['#000000', { h: 0, s: 0, l: 0 }]
    ])('hexToHsl(%s)', (hex, expected) => expect(hexToHsl(hex)).toEqual(expected));

    it('hslToHex returns lowercase hex', () =>
        expect(hslToHex({ h: 120, s: 100, l: 50 })).toBe('#00ff00'));

    it.each([
        ['#00FF00', true],
        ['#12', false],
        ['00ff00', false],
        ['#00ff0g', false]
    ])('isHexColor(%s) is %s', (value, expected) => expect(isHexColor(value)).toBe(expected));
});
