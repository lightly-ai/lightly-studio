import { describe, expect, test } from 'vitest';

import { getHoverPreviewState } from './hoverPreviewState';

describe('getHoverPreviewState', () => {
    const proxy = {
        location: (x: number, y: number) => ({ x: x * 10, y: y * 10 }),
        width: 400,
        height: 400
    };
    const defaults = {
        tooltip: { x: 20, y: 30, identifier: 'sample-a' },
        rangeSelectionActive: false,
        proxy,
        cardSize: 130
    };

    test('returns the sample and card position above the point', () => {
        expect(getHoverPreviewState(defaults)).toEqual({
            sampleId: 'sample-a',
            left: 200,
            top: 160
        });
    });

    test('returns null while a lasso is active, without a proxy, or without a sample id', () => {
        expect(getHoverPreviewState({ ...defaults, rangeSelectionActive: true })).toBeNull();
        expect(getHoverPreviewState({ ...defaults, proxy: null })).toBeNull();
        expect(getHoverPreviewState({ ...defaults, tooltip: null })).toBeNull();
        expect(getHoverPreviewState({ ...defaults, tooltip: { x: 20, y: 30 } })).toBeNull();
    });
});
