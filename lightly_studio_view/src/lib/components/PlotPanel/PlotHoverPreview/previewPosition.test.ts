import { describe, expect, it } from 'vitest';

import { getPreviewPosition } from './previewPosition';

describe('getPreviewPosition', () => {
    const defaults = { plotWidth: 400, cardSize: 128, margin: 4, offset: 10 };

    it('centers the card above the point', () => {
        expect(getPreviewPosition({ ...defaults, point: { x: 200, y: 300 } })).toEqual({
            left: 200,
            top: 162
        });
    });

    it('clamps horizontally at the plot edges', () => {
        expect(getPreviewPosition({ ...defaults, point: { x: 10, y: 300 } })?.left).toBe(68);
        expect(getPreviewPosition({ ...defaults, point: { x: 395, y: 300 } })?.left).toBe(332);
    });

    it('clamps at the top edge instead of flipping below the point', () => {
        expect(getPreviewPosition({ ...defaults, point: { x: 200, y: 30 } })?.top).toBe(4);
    });

    it('returns null when the plot is too narrow to contain the card and margins', () => {
        expect(
            getPreviewPosition({
                ...defaults,
                point: { x: 68, y: 300 },
                plotWidth: defaults.cardSize + 2 * defaults.margin - 1
            })
        ).toBeNull();
    });
});
