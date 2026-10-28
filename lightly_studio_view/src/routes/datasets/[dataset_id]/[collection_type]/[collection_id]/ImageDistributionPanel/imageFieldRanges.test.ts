import { describe, expect, it } from 'vitest';
import { applyImageFieldRange, selectImageFieldRanges } from './imageFieldRanges';

const bounds = { min_width: 100, max_width: 300, min_height: 10, max_height: 30 };

describe('selectImageFieldRanges', () => {
    it('keys the width and height filter by group ID', () => {
        expect(selectImageFieldRanges(bounds)).toEqual({
            'image:width': { min: 100, max: 300 },
            'image:height': { min: 10, max: 30 }
        });
    });

    it('returns no ranges before the bounds have loaded', () => {
        expect(selectImageFieldRanges(null)).toEqual({});
    });
});

describe('applyImageFieldRange', () => {
    it('sets the filter of the field to the whole pixels inside the range', () => {
        expect(
            applyImageFieldRange({
                field: 'width',
                bounds,
                values: bounds,
                range: { min: 150.5, max: 200.5 }
            })
        ).toEqual({ ...bounds, min_width: 151, max_width: 200 });
    });

    it('keeps the filter of the other field', () => {
        const values = { ...bounds, min_width: 120, max_width: 180 };

        expect(
            applyImageFieldRange({ field: 'height', bounds, values, range: { min: 20, max: 25 } })
        ).toEqual({ ...values, min_height: 20, max_height: 25 });
    });

    it('resets the filter when the current range is selected again', () => {
        const values = { ...bounds, min_height: 20, max_height: 25 };

        expect(
            applyImageFieldRange({ field: 'height', bounds, values, range: { min: 20, max: 25 } })
        ).toEqual(bounds);
    });

    it('keeps a range narrower than one pixel valid', () => {
        expect(
            applyImageFieldRange({
                field: 'width',
                bounds,
                values: bounds,
                range: { min: 150.2, max: 150.8 }
            })
        ).toEqual({ ...bounds, min_width: 151, max_width: 151 });
    });
});
