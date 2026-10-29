import { describe, expect, it } from 'vitest';
import { getPreviewMaskOpacity } from './previewMaskOpacity';

describe('getPreviewMaskOpacity', () => {
    it('uses the mask opacity scaled by the label alpha', () => {
        expect(getPreviewMaskOpacity({ maskOpacity: 0.6 })).toBeCloseTo(0.6);
        expect(getPreviewMaskOpacity({ maskOpacity: 0.8, labelAlpha: 0.5 })).toBeCloseTo(0.4);
    });

    it('keeps a minimum opacity so the preview stays visible', () => {
        expect(getPreviewMaskOpacity({ maskOpacity: 0 })).toBeCloseTo(0.3);
        expect(getPreviewMaskOpacity({ maskOpacity: 0.6, labelAlpha: 0 })).toBeCloseTo(0.3);
    });
});
