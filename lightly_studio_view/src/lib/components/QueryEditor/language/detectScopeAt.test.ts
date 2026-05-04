import { describe, expect, it } from 'vitest';
import { detectScopeAt } from './detectScopeAt';

describe('detectScopeAt', () => {
    it('returns image scope at top level by default', () => {
        const text = 'width > 100';
        expect(detectScopeAt(text, text.length)).toBe('image');
    });

    it('returns video scope when query starts with video prefix', () => {
        const text = 'video: fps == 30';
        expect(detectScopeAt(text, text.length)).toBe('video');
    });

    it('returns object_detection scope inside object_detection(...)', () => {
        const text = 'object_detection(label == "cat" AND width > 10)';
        const offset = text.indexOf('width') + 2;
        expect(detectScopeAt(text, offset)).toBe('object_detection');
    });

    it('returns classification scope inside classification(...)', () => {
        const text = 'classification(label == "car")';
        const offset = text.indexOf('label') + 2;
        expect(detectScopeAt(text, offset)).toBe('classification');
    });

    it('falls back to outer scope after nested expression closes', () => {
        const text = 'object_detection(label == "cat") AND width > 10';
        const offset = text.lastIndexOf('width') + 2;
        expect(detectScopeAt(text, offset)).toBe('image');
    });

    it('ignores pseudo tokens inside string literals while parsing scope frames', () => {
        const text = 'object_detection(label == "foo object_detection(bar)") AND width > 1';
        const offset = text.lastIndexOf('width') + 2;
        expect(detectScopeAt(text, offset)).toBe('image');
    });
});
