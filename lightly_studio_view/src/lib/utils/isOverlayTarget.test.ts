import { describe, expect, it } from 'vitest';
import { isOverlayTarget } from './isOverlayTarget';

describe('isOverlayTarget', () => {
    it.each(['role="dialog"', 'role="menu"', 'role="listbox"', 'data-popover-content'])(
        'recognizes an overlay and its descendants: %s',
        (attribute) => {
            const wrapper = document.createElement('div');
            wrapper.innerHTML = `<div ${attribute}><button></button></div>`;
            expect(isOverlayTarget(wrapper.firstElementChild)).toBe(true);
            expect(isOverlayTarget(wrapper.querySelector('button'))).toBe(true);
            expect(isOverlayTarget(wrapper)).toBe(false);
        }
    );
    it('ignores non-element targets', () => {
        expect(isOverlayTarget(null)).toBe(false);
        expect(isOverlayTarget(window)).toBe(false);
    });
});
