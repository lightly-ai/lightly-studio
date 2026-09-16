import { describe, expect, it } from 'vitest';
import { formatContextText, formatShowingText } from './statusBarText';

describe('formatShowingText', () => {
    it('shows the total when nothing is filtered out', () => {
        expect(formatShowingText({ total: 128, filtered: 128, itemType: 'images' })).toBe(
            'Showing 128 images'
        );
    });

    it('shows both counts once a filter narrows the view', () => {
        expect(formatShowingText({ total: 128, filtered: 12, itemType: 'images' })).toBe(
            'Showing 12 of 128 images'
        );
    });

    it('says nothing for an empty collection', () => {
        expect(formatShowingText({ total: 0, filtered: 0, itemType: 'images' })).toBe('');
    });
});

describe('formatContextText', () => {
    it('leads with the selection when one is active', () => {
        expect(formatContextText({ selectedCount: 3, sourceCount: 2, classCount: 71 })).toBe(
            '3 selected · 2 annotation sources'
        );
    });

    it('falls back to sources and classes with no selection', () => {
        expect(formatContextText({ selectedCount: 0, sourceCount: 2, classCount: 71 })).toBe(
            '2 annotation sources · 71 classes'
        );
    });

    it('singularises source and class', () => {
        expect(formatContextText({ selectedCount: 0, sourceCount: 1, classCount: 1 })).toBe(
            '1 annotation source · 1 class'
        );
    });

    it('drops the class count when there are no classes', () => {
        expect(formatContextText({ selectedCount: 0, sourceCount: 2, classCount: 0 })).toBe(
            '2 annotation sources'
        );
    });
});
