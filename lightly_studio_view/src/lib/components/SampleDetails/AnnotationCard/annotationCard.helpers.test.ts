import { describe, expect, it } from 'vitest';
import {
    getShortcutKeys,
    imageRectToScreen,
    isDeleteKey,
    isSearchStartKey,
    matchClasses,
    matchSources,
    placePanel,
    recentChips
} from './annotationCard.helpers';

const canvas = { left: 0, top: 0, right: 1000, bottom: 600 };
const panel = { width: 200, height: 100 };

describe('placePanel', () => {
    it('places the panel right of the box', () => {
        const box = { left: 100, top: 50, right: 300, bottom: 200 };

        expect(placePanel({ box, canvas, panel })).toEqual({ left: 308, top: 50 });
    });

    it('places the panel left of the box when the right side has no room', () => {
        const box = { left: 700, top: 50, right: 900, bottom: 200 };

        expect(placePanel({ box, canvas, panel })).toEqual({ left: 492, top: 50 });
    });

    it('keeps the panel on the canvas when neither side has room', () => {
        const box = { left: 100, top: 50, right: 900, bottom: 200 };

        expect(placePanel({ box, canvas, panel })).toEqual({ left: 800, top: 50 });
    });

    it('keeps the panel inside the canvas vertically', () => {
        expect(
            placePanel({ box: { left: 100, top: -40, right: 300, bottom: 80 }, canvas, panel }).top
        ).toBe(0);
        expect(
            placePanel({ box: { left: 100, top: 550, right: 300, bottom: 590 }, canvas, panel }).top
        ).toBe(500);
    });
});

describe('isDeleteKey', () => {
    const press = (overrides: Partial<Parameters<typeof isDeleteKey>[0]> = {}) =>
        isDeleteKey({
            key: 'Delete',
            target: document.body,
            repeat: false,
            altKey: false,
            ctrlKey: false,
            metaKey: false,
            ...overrides
        });

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
        const input = document.createElement('input');
        const menu = document.createElement('div');
        menu.setAttribute('role', 'listbox');
        const option = menu.appendChild(document.createElement('div'));

        expect(press({ key: 'Backspace', target: input })).toBe(false);
        expect(press({ target: option })).toBe(false);
    });
});

describe('imageRectToScreen', () => {
    it('maps an image box through the matrix', () => {
        expect(
            imageRectToScreen({ x: 5, y: 5, width: 10, height: 20 }, { a: 2, d: 2, e: 10, f: 20 })
        ).toEqual({ left: 20, top: 30, right: 40, bottom: 70 });
    });
});

describe('isSearchStartKey', () => {
    const press = (
        overrides: Partial<Parameters<typeof isSearchStartKey>[0]> = {},
        shortcutKeys: string[] = []
    ) =>
        isSearchStartKey(
            {
                key: 'k',
                target: document.body,
                repeat: false,
                altKey: false,
                ctrlKey: false,
                metaKey: false,
                ...overrides
            },
            shortcutKeys
        );

    it('starts on a letter or a digit', () => {
        expect(press()).toBe(true);
        expect(press({ key: 'K' })).toBe(true);
        expect(press({ key: '7' })).toBe(true);
    });

    it('keeps the shortcut letters for their shortcut', () => {
        expect(press({ key: 'v' }, ['v', 'b'])).toBe(false);
        expect(press({ key: 'B' }, ['v', 'b'])).toBe(false);
    });

    it('ignores other keys, modifiers and held keys', () => {
        expect(press({ key: 'Enter' })).toBe(false);
        expect(press({ key: ' ' })).toBe(false);
        expect(press({ ctrlKey: true })).toBe(false);
        expect(press({ metaKey: true })).toBe(false);
        expect(press({ repeat: true })).toBe(false);
    });

    it('ignores the keys while typing or inside an open menu', () => {
        const menu = document.createElement('div');
        menu.setAttribute('role', 'listbox');
        const option = menu.appendChild(document.createElement('div'));

        expect(press({ target: document.createElement('input') })).toBe(false);
        expect(press({ target: option })).toBe(false);
    });
});

describe('getShortcutKeys', () => {
    it('lowercases the keys and skips the empty ones', () => {
        expect(
            getShortcutKeys({
                key_hide_annotations: 'V',
                key_toolbar_bounding_box: 'b',
                key_toolbar_brush: null
            })
        ).toEqual(['v', 'b']);
    });
});

describe('matchClasses', () => {
    const names = ['bobcat', 'coyote', 'deer', 'raccoon'];

    it('lists recent classes first for an empty query', () => {
        expect(matchClasses({ names, recent: ['deer', 'coyote'], query: '' })).toEqual({
            matches: ['deer', 'coyote', 'bobcat', 'raccoon'],
            createName: null
        });
    });

    it('matches by substring and offers to create', () => {
        expect(matchClasses({ names, recent: [], query: 'co' })).toEqual({
            matches: ['coyote', 'raccoon'],
            createName: 'co'
        });
    });

    it('orders exact, prefix, then substring', () => {
        expect(
            matchClasses({ names: ['bobcat', 'category', 'cat'], recent: [], query: 'cat' })
        ).toEqual({ matches: ['cat', 'category', 'bobcat'], createName: null });
    });

    it('puts recent classes first within a tier', () => {
        expect(
            matchClasses({ names: ['cat', 'car', 'cab'], recent: ['cab'], query: 'ca' })
        ).toEqual({ matches: ['cab', 'car', 'cat'], createName: 'ca' });
    });

    it('ignores case', () => {
        expect(matchClasses({ names, recent: [], query: 'DEER' })).toEqual({
            matches: ['deer'],
            createName: null
        });
    });

    it('trims the query', () => {
        expect(matchClasses({ names, recent: [], query: '  fox ' })).toEqual({
            matches: [],
            createName: 'fox'
        });
    });
});

describe('matchSources', () => {
    const sources = [{ name: 'predictions' }, { name: 'labels' }, { name: 'model-preds' }];

    it('sorts alphabetically for an empty query', () => {
        expect(matchSources({ sources, query: '' }).map((s) => s.name)).toEqual([
            'labels',
            'model-preds',
            'predictions'
        ]);
    });

    it('puts prefix matches before substring matches', () => {
        expect(matchSources({ sources, query: 'PRE' }).map((s) => s.name)).toEqual([
            'predictions',
            'model-preds'
        ]);
    });
});

describe('recentChips', () => {
    const list = ['deer', 'bobcat', 'coyote', 'fox'];

    it('skips the current class', () => {
        expect(recentChips(list, 'deer')).toEqual(['bobcat', 'coyote', 'fox']);
    });

    it('keeps the first three without a current class', () => {
        expect(recentChips(list, null)).toEqual(['deer', 'bobcat', 'coyote']);
    });
});
