import { computeColorByKey } from './computeColorByKey';

describe('computeColorByKey', () => {
    test('returns consistent colors for the same key', () => {
        expect(computeColorByKey('label')).toEqual(computeColorByKey('label'));
    });

    test('returns different colors for different keys', () => {
        expect(computeColorByKey('cat')).not.toEqual(computeColorByKey('dog'));
    });

    test('returns rgba color and contrastColor strings', () => {
        const { color, contrastColor } = computeColorByKey('test');
        expect(color).toMatch(/^rgba\(\d+, \d+, \d+, [\d.]+\)$/);
        expect(contrastColor).toMatch(/^rgba\(\d+, \d+, \d+, [\d.]+\)$/);
    });

    test('applies alpha to the output', () => {
        const { color } = computeColorByKey('test', 0.5);
        expect(color).toContain('0.5');
    });

    test('clamps alpha below 0 to 0', () => {
        const { color } = computeColorByKey('test', -1);
        expect(color).toContain(', 0)');
    });

    test('clamps alpha above 1 to 1', () => {
        const { color } = computeColorByKey('test', 2);
        expect(color).toContain(', 1)');
    });

    test('default alpha is 1', () => {
        const { color } = computeColorByKey('test');
        expect(color).toContain(', 1)');
    });

    test('contrast color is the RGB inverse of the main color', () => {
        const { color, contrastColor } = computeColorByKey('label');
        const parse = (s: string) =>
            s
                .match(/rgba\((\d+), (\d+), (\d+)/)!
                .slice(1)
                .map(Number);
        const [r, g, b] = parse(color);
        const [cr, cg, cb] = parse(contrastColor);
        expect(cr).toBe(255 - r);
        expect(cg).toBe(255 - g);
        expect(cb).toBe(255 - b);
    });
});
