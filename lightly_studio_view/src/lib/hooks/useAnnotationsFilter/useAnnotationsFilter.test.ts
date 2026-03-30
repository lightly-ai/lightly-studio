import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import type { AnnotationLabel } from '$lib/services/types';

const selectedAnnotationFilterIds = writable<Set<string>>(new Set());
const setSelectedAnnotationFilterIds = vi.fn((id: string) => {
    selectedAnnotationFilterIds.update((state) => {
        if (state.has(id)) {
            state.delete(id);
        } else {
            state.add(id);
        }
        return state;
    });
});
const clearSelectedAnnotationFilterIds = vi.fn(() => {
    selectedAnnotationFilterIds.update((state) => {
        state.clear();
        return state;
    });
});

vi.mock('../useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        selectedAnnotationFilterIds,
        setSelectedAnnotationFilterIds,
        clearSelectedAnnotationFilterIds
    })
}));

vi.mock('../useTags/useTags', () => ({
    useTags: () => ({
        tagsSelected: writable(new Set<string>())
    })
}));

import {
    useSelectedAnnotationsFilter,
    useAnnotationsFilter
} from './useAnnotationsFilter';

describe('useSelectedAnnotationsFilter', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        selectedAnnotationFilterIds.set(new Set());
    });

    it('returns undefined annotationFilter when no labels selected', () => {
        const { annotationFilter } = useSelectedAnnotationsFilter();
        expect(get(annotationFilter)).toBeUndefined();
    });

    it('returns annotationFilter with filter_type and annotation_label_ids when labels selected', () => {
        selectedAnnotationFilterIds.set(new Set(['label-1', 'label-2']));
        const { annotationFilter } = useSelectedAnnotationsFilter();

        const filter = get(annotationFilter);
        expect(filter).toEqual({
            filter_type: 'annotations',
            annotation_label_ids: expect.arrayContaining(['label-1', 'label-2'])
        });
    });

    it('returns undefined annotationLabelIds when no labels selected', () => {
        const { annotationLabelIds } = useSelectedAnnotationsFilter();
        expect(get(annotationLabelIds)).toBeUndefined();
    });

    it('returns annotationLabelIds array when labels selected', () => {
        selectedAnnotationFilterIds.set(new Set(['label-1']));
        const { annotationLabelIds } = useSelectedAnnotationsFilter();
        expect(get(annotationLabelIds)).toEqual(['label-1']);
    });

    it('returns selectedAnnotationFilterIdsArray as string[]', () => {
        selectedAnnotationFilterIds.set(new Set(['a', 'b']));
        const { selectedAnnotationFilterIdsArray } = useSelectedAnnotationsFilter();
        expect(get(selectedAnnotationFilterIdsArray)).toEqual(
            expect.arrayContaining(['a', 'b'])
        );
    });

    it('toggleSelectedAnnotationFilterId adds and removes ids', () => {
        const { toggleSelectedAnnotationFilterId } = useSelectedAnnotationsFilter();

        toggleSelectedAnnotationFilterId('label-1');
        expect(setSelectedAnnotationFilterIds).toHaveBeenCalledWith('label-1');
    });

    it('clearSelectedAnnotationFilterIds clears all', () => {
        selectedAnnotationFilterIds.set(new Set(['label-1', 'label-2']));
        const { clearSelectedAnnotationFilterIds: clear } = useSelectedAnnotationsFilter();

        clear();
        expect(clearSelectedAnnotationFilterIds).toHaveBeenCalled();
    });
});

describe('useAnnotationsFilter', () => {
    const mockLabels: AnnotationLabel[] = [
        { annotation_label_id: 'id-1', annotation_label_name: 'cat' },
        { annotation_label_id: 'id-2', annotation_label_name: 'dog' }
    ] as AnnotationLabel[];

    let annotationLabels: ReturnType<typeof writable<AnnotationLabel[] | undefined>>;

    beforeEach(() => {
        vi.clearAllMocks();
        selectedAnnotationFilterIds.set(new Set());
        annotationLabels = writable<AnnotationLabel[] | undefined>(mockLabels);
    });

    it('returns empty annotationFilters when no counts set', () => {
        const { annotationFilters } = useAnnotationsFilter({
            annotationLabels
        });
        expect(get(annotationFilters)).toEqual([]);
    });

    it('returns annotationFilters with selection state when counts are set', () => {
        selectedAnnotationFilterIds.set(new Set(['id-1']));

        const { annotationFilters, setAnnotationCounts } = useAnnotationsFilter({
            annotationLabels
        });

        setAnnotationCounts([
            { label_name: 'cat', total_count: 10, current_count: 5 },
            { label_name: 'dog', total_count: 8 }
        ]);

        const filters = get(annotationFilters);
        expect(filters).toEqual([
            { label_name: 'cat', total_count: 10, current_count: 5, selected: true },
            { label_name: 'dog', total_count: 8, selected: false }
        ]);
    });

    it('toggleAnnotationFilterSelection maps label name to id', () => {
        const { toggleAnnotationFilterSelection } = useAnnotationsFilter({
            annotationLabels
        });

        toggleAnnotationFilterSelection('cat');
        expect(setSelectedAnnotationFilterIds).toHaveBeenCalledWith('id-1');
    });

    it('toggleAnnotationFilterSelection does nothing for unknown label', () => {
        const { toggleAnnotationFilterSelection } = useAnnotationsFilter({
            annotationLabels
        });

        toggleAnnotationFilterSelection('unknown');
        expect(setSelectedAnnotationFilterIds).not.toHaveBeenCalled();
    });

    it('toggling off removes label and returns undefined filter', () => {
        selectedAnnotationFilterIds.set(new Set(['id-1']));

        const { annotationFilter, toggleAnnotationFilterSelection } = useAnnotationsFilter({
            annotationLabels
        });

        // Toggle off
        toggleAnnotationFilterSelection('cat');

        expect(get(annotationFilter)).toBeUndefined();
    });

    it('returns annotationFilterLabels mapping', () => {
        const { annotationFilterLabels } = useAnnotationsFilter({
            annotationLabels
        });

        expect(get(annotationFilterLabels)).toEqual({
            cat: 'id-1',
            dog: 'id-2'
        });
    });

    it('returns empty annotationFilterLabels when labels undefined', () => {
        annotationLabels.set(undefined);
        const { annotationFilterLabels } = useAnnotationsFilter({
            annotationLabels
        });

        expect(get(annotationFilterLabels)).toEqual({});
    });

    it('selectedAnnotationFilterNames returns selected label names', () => {
        selectedAnnotationFilterIds.set(new Set(['id-2']));

        const { selectedAnnotationFilterNames } = useAnnotationsFilter({
            annotationLabels
        });

        expect(get(selectedAnnotationFilterNames)).toEqual(['dog']);
    });
});
