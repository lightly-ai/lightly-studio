import { describe, expect, it } from 'vitest';
import { isDeleteKey, isRelabelKey } from './keyPress';

const plainPress = {
    target: document.body,
    repeat: false,
    altKey: false,
    ctrlKey: false,
    metaKey: false
};

const listboxOption = () => {
    const menu = document.createElement('div');
    menu.setAttribute('role', 'listbox');
    return menu.appendChild(document.createElement('div'));
};

describe('isDeleteKey', () => {
    const press = (overrides: Partial<Parameters<typeof isDeleteKey>[0]> = {}) =>
        isDeleteKey({ ...plainPress, key: 'Delete', ...overrides });

    it('deletes on Delete and Backspace', () => {
        expect(press()).toBe(true);
        expect(press({ key: 'Backspace' })).toBe(true);
    });

    it('ignores other keys and held keys', () => {
        expect(press({ key: 'd' })).toBe(false);
        expect(press({ repeat: true })).toBe(false);
    });

    it('ignores the keys with a modifier', () => {
        expect(press({ metaKey: true })).toBe(false);
        expect(press({ ctrlKey: true })).toBe(false);
        expect(press({ altKey: true })).toBe(false);
    });

    it('ignores the keys while typing or inside an open menu', () => {
        expect(press({ key: 'Backspace', target: document.createElement('input') })).toBe(false);
        expect(press({ target: listboxOption() })).toBe(false);
    });
});

describe('isRelabelKey', () => {
    const press = (overrides: Partial<Parameters<typeof isRelabelKey>[0]> = {}) =>
        isRelabelKey({ ...plainPress, key: 'Enter', ...overrides });

    it('opens on Enter', () => {
        expect(press()).toBe(true);
    });

    it('ignores letters, modifiers and held keys', () => {
        expect(press({ key: 'k' })).toBe(false);
        expect(press({ ctrlKey: true })).toBe(false);
        expect(press({ metaKey: true })).toBe(false);
        expect(press({ repeat: true })).toBe(false);
    });

    it('ignores the key while typing or inside an open menu', () => {
        expect(press({ target: document.createElement('input') })).toBe(false);
        expect(press({ target: listboxOption() })).toBe(false);
    });

    it('leaves Enter to a focused button on the card, not to one elsewhere', () => {
        const card = document.createElement('div');
        card.setAttribute('data-annotation-card', '');
        const chip = card.appendChild(document.createElement('button'));

        expect(press({ target: chip })).toBe(false);
        expect(press({ target: document.createElement('button') })).toBe(true);
    });
});
