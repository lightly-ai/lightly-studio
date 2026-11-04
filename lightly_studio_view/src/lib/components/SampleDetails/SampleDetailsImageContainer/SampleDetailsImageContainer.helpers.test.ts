import { describe, expect, it } from 'vitest';
import { getDrawerLabel, isPanEnabled } from './SampleDetailsImageContainer.helpers';

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

describe('getDrawerLabel', () => {
    it('uses the sticky class when nothing is selected', () => {
        expect(
            getDrawerLabel({ isAnnotationSelected: false, contextLabel: 'cat', stickyClass: 'dog' })
        ).toBe('dog');
    });

    it('has no class when nothing is selected and no class is sticky', () => {
        expect(
            getDrawerLabel({ isAnnotationSelected: false, contextLabel: 'cat', stickyClass: undefined })
        ).toBeNull();
    });

    it('uses the class of the selected annotation', () => {
        expect(
            getDrawerLabel({ isAnnotationSelected: true, contextLabel: 'cat', stickyClass: 'dog' })
        ).toBe('cat');
    });
});
