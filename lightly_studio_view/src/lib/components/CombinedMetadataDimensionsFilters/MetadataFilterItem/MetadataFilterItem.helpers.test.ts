import { describe, expect, it } from 'vitest';
import {
    clampMetadataValuesToMax,
    getMetadataSliderMax,
    getMetadataSliderStep,
    getSliderDisplayMaxValue
} from './MetadataFilterItem.helpers';

describe('MetadataFilterItem.helpers', () => {
    describe('getMetadataSliderStep', () => {
        it('returns rounded integer step for integer metadata', () => {
            const step = getMetadataSliderStep(0, 4500, true);

            expect(step).toBe(5);
        });

        it('returns a minimum step of 1 when integer range is non-positive', () => {
            const step = getMetadataSliderStep(12, 12, true);

            expect(step).toBe(1);
        });

        it('returns precise float step for float metadata', () => {
            const step = getMetadataSliderStep(0, 1, false);

            expect(step).toBe(0.001);
        });

        it('returns fallback float step when float range is non-positive', () => {
            const step = getMetadataSliderStep(3.5, 3.5, false);

            expect(step).toBe(0.001);
        });
    });

    describe('getMetadataSliderMax', () => {
        it('keeps max when it is on the step grid', () => {
            expect(getMetadataSliderMax(0, 10, 2)).toBe(10);
        });

        it('extends max by one step when it is off-grid', () => {
            expect(getMetadataSliderMax(0, 10, 3)).toBe(13);
        });
    });

    describe('getSliderDisplayMaxValue', () => {
        it('uses virtual slider max when selected value reached bound max', () => {
            expect(getSliderDisplayMaxValue(10, 10, 13)).toBe(13);
        });

        it('keeps selected value when below bound max', () => {
            expect(getSliderDisplayMaxValue(9, 10, 13)).toBe(9);
        });
    });

    describe('clampMetadataValuesToMax', () => {
        it('clamps values above the bound max', () => {
            expect(clampMetadataValuesToMax([12, 15], 10)).toEqual([10, 10]);
        });

        it('keeps values that are already below bound max', () => {
            expect(clampMetadataValuesToMax([5, 9], 10)).toEqual([5, 9]);
        });
    });
});
