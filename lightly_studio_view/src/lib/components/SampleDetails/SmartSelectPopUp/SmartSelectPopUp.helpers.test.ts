import { describe, expect, it } from 'vitest';
import { getSmartSelectHint } from './SmartSelectPopUp.helpers';

describe('getSmartSelectHint', () => {
    it('lists only the supported interactions', () => {
        expect(
            getSmartSelectHint({ positivePoints: true, negativePoints: true, boxes: true })
        ).toBe('Click to add, shift-click to remove, drag to box.');
        expect(
            getSmartSelectHint({ positivePoints: false, negativePoints: false, boxes: true })
        ).toBe('Drag to box.');
    });
});
