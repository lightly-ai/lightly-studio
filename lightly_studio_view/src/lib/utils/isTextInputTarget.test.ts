import { describe, expect, it } from 'vitest';
import { isTextInputTarget } from './isTextInputTarget';

describe('isTextInputTarget', () => {
    it('returns true for input and textarea elements', () => {
        expect(isTextInputTarget(document.createElement('input'))).toBe(true);
        expect(isTextInputTarget(document.createElement('textarea'))).toBe(true);
    });

    it('returns true for contenteditable elements', () => {
        const editableDiv = document.createElement('div');
        editableDiv.contentEditable = 'true';

        expect(isTextInputTarget(editableDiv)).toBe(true);
    });

    it('returns false for non-text elements and null', () => {
        expect(isTextInputTarget(document.createElement('button'))).toBe(false);
        expect(isTextInputTarget(null)).toBe(false);
    });
});
