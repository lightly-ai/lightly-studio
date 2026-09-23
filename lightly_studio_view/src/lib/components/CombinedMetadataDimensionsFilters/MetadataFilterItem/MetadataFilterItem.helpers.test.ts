import { describe, expect, it } from 'vitest';
import {
    FLOAT_SLIDER_TICKS,
    fromTick,
    getSliderTickCount,
    toTick
} from './MetadataFilterItem.helpers';

describe('MetadataFilterItem.helpers', () => {
    const solarAngle = { min: -75.89126551973673, max: 87.50941362154188 };
    const floatTicks = getSliderTickCount(solarAngle, false);

    describe('getSliderTickCount', () => {
        it('uses the fixed float resolution for float fields', () => {
            expect(getSliderTickCount(solarAngle, false)).toBe(FLOAT_SLIDER_TICKS);
        });

        it('uses one tick per integer for integer fields', () => {
            expect(getSliderTickCount({ min: 0, max: 1712 }, true)).toBe(1712);
        });

        it('never returns fewer than one tick for a degenerate range', () => {
            expect(getSliderTickCount({ min: 5, max: 5 }, true)).toBe(1);
        });
    });

    describe('toTick', () => {
        it('maps the bounds to the tick endpoints', () => {
            expect(toTick(solarAngle.min, solarAngle, floatTicks)).toBe(0);
            expect(toTick(solarAngle.max, solarAngle, floatTicks)).toBe(floatTicks);
        });

        it('maps the midpoint to the middle tick', () => {
            const mid = (solarAngle.min + solarAngle.max) / 2;

            expect(toTick(mid, solarAngle, floatTicks)).toBe(floatTicks / 2);
        });

        it('clamps values outside the bounds into the tick domain', () => {
            expect(toTick(solarAngle.min - 100, solarAngle, floatTicks)).toBe(0);
            expect(toTick(solarAngle.max + 100, solarAngle, floatTicks)).toBe(floatTicks);
        });

        it('returns 0 for a degenerate range instead of dividing by zero', () => {
            expect(toTick(5, { min: 5, max: 5 }, 1)).toBe(0);
        });
    });

    describe('fromTick', () => {
        it('returns the exact bounds at the tick endpoints', () => {
            expect(fromTick(0, solarAngle, floatTicks, false)).toBe(solarAngle.min);
            expect(fromTick(floatTicks, solarAngle, floatTicks, false)).toBe(solarAngle.max);
        });

        it('clamps ticks outside the domain to the bounds', () => {
            expect(fromTick(-10, solarAngle, floatTicks, false)).toBe(solarAngle.min);
            expect(fromTick(floatTicks + 10, solarAngle, floatTicks, false)).toBe(solarAngle.max);
        });

        it('keeps fractional precision for float metadata fields', () => {
            expect(Number.isInteger(fromTick(500, solarAngle, floatTicks, false))).toBe(false);
        });
    });

    describe('round-trip', () => {
        it('recovers interior float values within one tick of granularity', () => {
            const tickSize = (solarAngle.max - solarAngle.min) / floatTicks;
            const original = 12.3456;

            const recovered = fromTick(
                toTick(original, solarAngle, floatTicks),
                solarAngle,
                floatTicks,
                false
            );

            expect(Math.abs(recovered - original)).toBeLessThanOrEqual(tickSize);
        });

        it('recovers the float bounds exactly', () => {
            expect(
                fromTick(
                    toTick(solarAngle.min, solarAngle, floatTicks),
                    solarAngle,
                    floatTicks,
                    false
                )
            ).toBe(solarAngle.min);
            expect(
                fromTick(
                    toTick(solarAngle.max, solarAngle, floatTicks),
                    solarAngle,
                    floatTicks,
                    false
                )
            ).toBe(solarAngle.max);
        });

        // Regression: a fixed 1000-tick domain dropped integers once the span exceeded it
        // (e.g. 0..1712 could not select 1). Per-integer ticks must keep every integer selectable.
        it('makes every integer selectable for a wide integer field', () => {
            const bound = { min: 0, max: 1712 };
            const ticks = getSliderTickCount(bound, true);

            for (let value = bound.min; value <= bound.max; value++) {
                expect(fromTick(toTick(value, bound, ticks), bound, ticks, true)).toBe(value);
            }
        });
    });
});
