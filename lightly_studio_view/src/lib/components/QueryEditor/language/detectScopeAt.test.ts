import { describe, expect, it } from 'vitest';
import { detectScopeAt } from './detectScopeAt';

describe('detectScopeAt', () => {
    it('returns image scope at top level by default', () => {
        const text = 'width > 100';
        expect(detectScopeAt(text, text.length)).toBe('image');
    });

    it('returns video scope when query starts with video prefix', () => {
        const text = 'video: fps = 30';
        expect(detectScopeAt(text, text.length)).toBe('video');
    });

    it('returns object_detection scope inside object_detection(...)', () => {
        const text = 'object_detection(class_name = "cat" AND width > 10)';
        const offset = text.indexOf('width') + 2;
        expect(detectScopeAt(text, offset)).toBe('object_detection');
    });

    it('returns classification scope inside classification(...)', () => {
        const text = 'classification(class_name = "car")';
        const offset = text.indexOf('class_name') + 2;
        expect(detectScopeAt(text, offset)).toBe('classification');
    });

    it('returns segmentation_mask scope inside segmentation_mask(...)', () => {
        const text = 'segmentation_mask(class_name = "road" AND width > 10)';
        const offset = text.indexOf('width') + 2;
        expect(detectScopeAt(text, offset)).toBe('segmentation_mask');
    });

    it('falls back to outer scope after nested expression closes', () => {
        const text = 'object_detection(class_name = "cat") AND width > 10';
        const offset = text.lastIndexOf('width') + 2;
        expect(detectScopeAt(text, offset)).toBe('image');
    });

    it('ignores pseudo tokens inside string literals while parsing scope frames', () => {
        const text = 'object_detection(class_name = "foo object_detection(bar)") AND width > 1';
        const offset = text.lastIndexOf('width') + 2;
        expect(detectScopeAt(text, offset)).toBe('image');
    });
});
