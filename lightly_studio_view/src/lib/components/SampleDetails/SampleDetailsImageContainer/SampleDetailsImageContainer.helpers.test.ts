import { describe, expect, it } from 'vitest';
import { isPanEnabled } from './SampleDetailsImageContainer.helpers';

const params = {
    isDrawing: false,
    isErasing: false,
    blocksPan: false
};

describe('isPanEnabled', () => {
    it('enables panning without an active drawing tool', () => {
        expect(isPanEnabled(params)).toBe(true);
    });

    it('disables panning while drawing or erasing', () => {
        expect(isPanEnabled({ ...params, isDrawing: true })).toBe(false);
        expect(isPanEnabled({ ...params, isErasing: true })).toBe(false);
    });

    it('disables panning for an assisted labeling tool that blocks it', () => {
        expect(isPanEnabled({ ...params, blocksPan: true })).toBe(false);
    });
});
