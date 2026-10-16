import { describe, expect, it } from 'vitest';
import { isPanEnabled } from './SampleDetailsImageContainer.helpers';

const params = {
    isEditingMode: true,
    isDrawing: false,
    isErasing: false,
    status: 'cursor'
};

describe('isPanEnabled', () => {
    it('enables panning without an active drawing tool', () => {
        expect(isPanEnabled(params)).toBe(true);
    });

    it('disables panning while drawing or erasing', () => {
        expect(isPanEnabled({ ...params, isDrawing: true })).toBe(false);
        expect(isPanEnabled({ ...params, isErasing: true })).toBe(false);
    });

    it('disables panning for smart select in edit mode only', () => {
        expect(isPanEnabled({ ...params, status: 'smart-select' })).toBe(false);
        expect(isPanEnabled({ ...params, status: 'smart-select', isEditingMode: false })).toBe(
            true
        );
    });
});
