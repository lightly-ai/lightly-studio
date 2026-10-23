import { describe, expect, it } from 'vitest';
import { isPanEnabled } from './SampleDetailsImageContainer.helpers';

const params = {
    isDrawing: false,
    isErasing: false,
    status: 'cursor' as const
};

describe('isPanEnabled', () => {
    it('enables panning without an active drawing tool', () => {
        expect(isPanEnabled(params)).toBe(true);
    });

    it('disables panning while drawing or erasing', () => {
        expect(isPanEnabled({ ...params, isDrawing: true })).toBe(false);
        expect(isPanEnabled({ ...params, isErasing: true })).toBe(false);
    });

    it('disables panning for assisted labeling tools', () => {
        expect(isPanEnabled({ ...params, status: 'smart-select' })).toBe(false);
    });
});
