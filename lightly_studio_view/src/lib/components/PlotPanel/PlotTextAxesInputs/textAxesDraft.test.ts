import { describe, expect, it } from 'vitest';
import { areTextAxesEqual } from './textAxesDraft';

const AXES = {
    x: { negative: 'night', positive: 'day' },
    y: { negative: 'indoors', positive: 'outdoors' }
};

describe('areTextAxesEqual', () => {
    it.each([
        // A deep copy, so the texts are compared and not the references.
        ['the same texts', structuredClone(AXES), true],
        ['another x text', { ...AXES, x: { ...AXES.x, positive: 'noon' } }, false],
        ['another y text', { ...AXES, y: { ...AXES.y, negative: 'garage' } }, false],
        ['no axes', null, false]
    ])('compares the axes with %s', (_, other, expected) => {
        expect(areTextAxesEqual(AXES, other)).toBe(expected);
    });
});
