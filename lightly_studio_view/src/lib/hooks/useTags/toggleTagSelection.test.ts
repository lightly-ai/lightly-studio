import { describe, expect, it, vi } from 'vitest';
import { toggleTagSelection } from './toggleTagSelection';
import type { TagView as Tag } from '$lib/services/types';

const tags: Tag[] = [
    {
        tag_id: 't1',
        name: 'Blurry',
        kind: 'sample',
        created_at: new Date(0),
        updated_at: new Date(0)
    },
    {
        tag_id: 't2',
        name: 'Overexposed',
        kind: 'sample',
        created_at: new Date(0),
        updated_at: new Date(0)
    }
];

const defaultParams = {
    tagId: 't1',
    collectionId: 'col-1',
    currentSelected: new Set<string>(),
    allTags: tags
};

describe('toggleTagSelection', () => {
    it('calls updateSelected with the tag added when it was not selected', () => {
        const updateSelected = vi.fn();
        const trackEvent = vi.fn();

        toggleTagSelection({ ...defaultParams, updateSelected, trackEvent });

        expect(updateSelected).toHaveBeenCalledWith('col-1', new Set(['t1']));
    });

    it('calls updateSelected with the tag removed when it was already selected', () => {
        const updateSelected = vi.fn();
        const trackEvent = vi.fn();

        toggleTagSelection({
            ...defaultParams,
            currentSelected: new Set(['t1', 't2']),
            updateSelected,
            trackEvent
        });

        expect(updateSelected).toHaveBeenCalledWith('col-1', new Set(['t2']));
    });

    it('fires grid_filter_toggled with action selected when tag was not selected', () => {
        const updateSelected = vi.fn();
        const trackEvent = vi.fn();

        toggleTagSelection({ ...defaultParams, updateSelected, trackEvent });

        expect(trackEvent).toHaveBeenCalledWith('grid_filter_toggled', {
            collection_id: 'col-1',
            filter_type: 'tag',
            filter_value: 'Blurry',
            action: 'selected',
            active_count: 1
        });
    });

    it('fires grid_filter_toggled with action unselected when tag was already selected', () => {
        const updateSelected = vi.fn();
        const trackEvent = vi.fn();

        toggleTagSelection({
            ...defaultParams,
            currentSelected: new Set(['t1', 't2']),
            updateSelected,
            trackEvent
        });

        expect(trackEvent).toHaveBeenCalledWith('grid_filter_toggled', {
            collection_id: 'col-1',
            filter_type: 'tag',
            filter_value: 'Blurry',
            action: 'unselected',
            active_count: 1
        });
    });

    it('falls back to tagId as filter_value when tag is not found in allTags', () => {
        const updateSelected = vi.fn();
        const trackEvent = vi.fn();

        toggleTagSelection({ ...defaultParams, tagId: 'unknown', updateSelected, trackEvent });

        expect(trackEvent).toHaveBeenCalledWith('grid_filter_toggled', {
            collection_id: 'col-1',
            filter_type: 'tag',
            filter_value: 'unknown',
            action: 'selected',
            active_count: 1
        });
    });

    it('reports active_count as the size of the new selection', () => {
        const updateSelected = vi.fn();
        const trackEvent = vi.fn();

        toggleTagSelection({
            ...defaultParams,
            tagId: 't2',
            currentSelected: new Set(['t1']),
            updateSelected,
            trackEvent
        });

        expect(trackEvent).toHaveBeenCalledWith(
            'grid_filter_toggled',
            expect.objectContaining({ active_count: 2 })
        );
    });
});
