import { describe, expect, it } from 'vitest';
import { isEditableTarget, isSelectAllShortcut } from './selectAllShortcut';

const keydown = (init: KeyboardEventInit) => new KeyboardEvent('keydown', init);

describe('isSelectAllShortcut', () => {
    it('accepts Ctrl+A and Cmd+A', () => {
        expect(isSelectAllShortcut(keydown({ key: 'a', ctrlKey: true }))).toBe(true);
        expect(isSelectAllShortcut(keydown({ key: 'a', metaKey: true }))).toBe(true);
    });

    it('rejects an unmodified "a" and other modified keys', () => {
        expect(isSelectAllShortcut(keydown({ key: 'a' }))).toBe(false);
        expect(isSelectAllShortcut(keydown({ key: 's', ctrlKey: true }))).toBe(false);
    });
});

describe('isEditableTarget', () => {
    it('treats inputs and contenteditable elements as owning the shortcut', () => {
        expect(isEditableTarget(document.createElement('input'))).toBe(true);
        expect(isEditableTarget(document.createElement('textarea'))).toBe(true);

        // jsdom does not derive isContentEditable from the attribute, so set the
        // property the browser would have computed.
        const editable = Object.defineProperty(document.createElement('div'), 'isContentEditable', {
            value: true
        });
        expect(isEditableTarget(editable)).toBe(true);
    });

    it('leaves the shortcut to the grid elsewhere', () => {
        expect(isEditableTarget(document.createElement('div'))).toBe(false);
        expect(isEditableTarget(null)).toBe(false);
    });
});
