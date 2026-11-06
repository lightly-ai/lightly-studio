import { describe, expect, it } from 'vitest';
import { canInferFromPoints } from './SmartSelectOverlay.helpers';

describe('SmartSelectOverlay.helpers', () => {
    it('needs a positive point to infer', () => {
        expect(canInferFromPoints([{ x: 0, y: 0, positive: false }])).toBe(false);
        expect(
            canInferFromPoints([
                { x: 0, y: 0, positive: false },
                { x: 0, y: 0, positive: true }
            ])
        ).toBe(true);
    });
});
