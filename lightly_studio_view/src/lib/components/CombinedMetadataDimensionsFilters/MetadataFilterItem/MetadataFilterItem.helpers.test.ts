import { describe, expect, it } from 'vitest';
import { SLIDER_TICKS, fromTick, toTick } from './MetadataFilterItem.helpers';

describe('MetadataFilterItem.helpers', () => {
    const solarAngle = { min: -75.89126551973673, max: 87.50941362154188 };

    describe('toTick', () => {
        it('maps the bounds to the tick endpoints', () => {
            expect(toTick(solarAngle.min, solarAngle)).toBe(0);
            expect(toTick(solarAngle.max, solarAngle)).toBe(SLIDER_TICKS);
        });

        it('maps the midpoint to the middle tick', () => {
            const mid = (solarAngle.min + solarAngle.max) / 2;

            expect(toTick(mid, solarAngle)).toBe(SLIDER_TICKS / 2);
        });

        it('is monotonic across the range', () => {
            expect(toTick(solarAngle.min, solarAngle)).toBeLessThanOrEqual(
                toTick(solarAngle.max, solarAngle)
            );
        });

        it('clamps values outside the bounds into the tick domain', () => {
            expect(toTick(solarAngle.min - 100, solarAngle)).toBe(0);
            expect(toTick(solarAngle.max + 100, solarAngle)).toBe(SLIDER_TICKS);
        });

        it('returns 0 for a degenerate range instead of dividing by zero', () => {
            expect(toTick(5, { min: 5, max: 5 })).toBe(0);
        });
    });

    describe('fromTick', () => {
        it('returns the exact bounds at the tick endpoints', () => {
            expect(fromTick(0, solarAngle, false)).toBe(solarAngle.min);
            expect(fromTick(SLIDER_TICKS, solarAngle, false)).toBe(solarAngle.max);
        });

        it('clamps ticks outside the domain to the bounds', () => {
            expect(fromTick(-10, solarAngle, false)).toBe(solarAngle.min);
            expect(fromTick(SLIDER_TICKS + 10, solarAngle, false)).toBe(solarAngle.max);
        });

        it('rounds to whole numbers for integer metadata fields', () => {
            const bound = { min: 0, max: 1712 };
            const value = fromTick(500, bound, true);

            expect(Number.isInteger(value)).toBe(true);
        });

        it('keeps fractional precision for float metadata fields', () => {
            const value = fromTick(500, solarAngle, false);

            expect(Number.isInteger(value)).toBe(false);
        });
    });

    describe('round-trip', () => {
        it('recovers interior values within one tick of granularity', () => {
            const tickSize = (solarAngle.max - solarAngle.min) / SLIDER_TICKS;
            const original = 12.3456;

            const recovered = fromTick(toTick(original, solarAngle), solarAngle, false);

            expect(Math.abs(recovered - original)).toBeLessThanOrEqual(tickSize);
        });

        it('recovers the bounds exactly', () => {
            expect(fromTick(toTick(solarAngle.min, solarAngle), solarAngle, false)).toBe(
                solarAngle.min
            );
            expect(fromTick(toTick(solarAngle.max, solarAngle), solarAngle, false)).toBe(
                solarAngle.max
            );
        });
    });
});
