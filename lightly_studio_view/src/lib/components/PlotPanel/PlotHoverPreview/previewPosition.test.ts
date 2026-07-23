import { describe, expect, it } from 'vitest';

import { getPreviewPosition } from './previewPosition';

describe('getPreviewPosition', () => {
    const defaults = { plotWidth: 400, cardSize: 130, margin: 4, offset: 10 };

    it('centers the card above the point', () => {
        expect(getPreviewPosition({ ...defaults, point: { x: 200, y: 300 } })).toEqual({
            left: 200,
            top: 160
        });
    });

    it('clamps horizontally at the plot edges', () => {
        expect(getPreviewPosition({ ...defaults, point: { x: 10, y: 300 } }).left).toBe(69);
        expect(getPreviewPosition({ ...defaults, point: { x: 395, y: 300 } }).left).toBe(331);
    });

    it('clamps at the top edge instead of flipping below the point', () => {
        expect(getPreviewPosition({ ...defaults, point: { x: 200, y: 30 } }).top).toBe(4);
    });
});
