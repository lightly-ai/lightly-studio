import { describe, expect, it } from 'vitest';
import { isOverlayTarget } from './isOverlayTarget';

const createOverlayChild = (attribute: string, value: string): HTMLElement => {
    const overlay = document.createElement('div');
    overlay.setAttribute(attribute, value);

    const input = document.createElement('input');
    overlay.appendChild(input);

    return input;
};

describe('isOverlayTarget', () => {
    it.each([
        ['role', 'dialog'],
        ['role', 'menu'],
        ['role', 'listbox'],
        ['data-popover-content', '']
    ])('returns true for an element inside %s="%s"', (attribute, value) => {
        expect(isOverlayTarget(createOverlayChild(attribute, value))).toBe(true);
    });

    it('returns true for the overlay element itself', () => {
        const overlay = document.createElement('div');
        overlay.setAttribute('role', 'dialog');

        expect(isOverlayTarget(overlay)).toBe(true);
    });

    it('returns false for an element outside any overlay and for null', () => {
        expect(isOverlayTarget(document.createElement('input'))).toBe(false);
        expect(isOverlayTarget(null)).toBe(false);
    });
});
