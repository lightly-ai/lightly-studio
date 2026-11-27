import { describe, expect, it } from 'vitest';
import { showsEgoRangeOverlay } from './showsEgoRangeOverlay';

describe('showsEgoRangeOverlay', () => {
    it('draws the overlay in the 3D and Top views', () => {
        expect(showsEgoRangeOverlay('perspective')).toBe(true);
        expect(showsEgoRangeOverlay('top')).toBe(true);
    });

    it('does not draw the overlay in the Side and Front views', () => {
        expect(showsEgoRangeOverlay('side')).toBe(false);
        expect(showsEgoRangeOverlay('front')).toBe(false);
    });
});
