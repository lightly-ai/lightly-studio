import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useAnnotationCollectionsFilter } from './useAnnotationCollectionsFilter';

describe('useAnnotationCollectionsFilter', () => {
    it('marks the selection as initialized once it is explicitly set, even to empty', () => {
        const { isSelectionInitialized, selectedCollectionIds, setSelectedCollectionIds } =
            useAnnotationCollectionsFilter();

        expect(get(isSelectionInitialized)).toBe(false);

        setSelectedCollectionIds([]);

        expect(get(isSelectionInitialized)).toBe(true);
        expect(get(selectedCollectionIds)).toEqual([]);
    });
});
