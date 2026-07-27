import { describe, expect, it, vi } from 'vitest';
import { handleAnnotationSourceFilterChange } from './handleAnnotationSourceFilterChange';

const items = [
    { id: 'c1', name: 'Dogs' },
    { id: 'c2', name: 'Cats' }
];

describe('handleAnnotationSourceFilterChange', () => {
    it('calls setSelectedCollectionIds with the new ids', () => {
        const setSelectedCollectionIds = vi.fn();
        const trackEvent = vi.fn();

        handleAnnotationSourceFilterChange({
            newIds: ['c2'],
            prevIds: ['c1', 'c2'],
            items,
            collectionId: 'col-1',
            setSelectedCollectionIds,
            trackEvent
        });

        expect(setSelectedCollectionIds).toHaveBeenCalledWith(['c2']);
    });

    it('fires grid_filter_toggled with action unselected when a source is deselected', () => {
        const setSelectedCollectionIds = vi.fn();
        const trackEvent = vi.fn();

        handleAnnotationSourceFilterChange({
            newIds: ['c2'],
            prevIds: ['c1', 'c2'],
            items,
            collectionId: 'col-1',
            setSelectedCollectionIds,
            trackEvent
        });

        expect(trackEvent).toHaveBeenCalledWith('grid_filter_toggled', {
            collection_id: 'col-1',
            filter_type: 'annotation_source',
            filter_value: 'Dogs',
            action: 'unselected',
            active_count: 1
        });
    });

    it('fires grid_filter_toggled with action selected when a source is selected', () => {
        const setSelectedCollectionIds = vi.fn();
        const trackEvent = vi.fn();

        handleAnnotationSourceFilterChange({
            newIds: ['c1', 'c2'],
            prevIds: ['c2'],
            items,
            collectionId: 'col-1',
            setSelectedCollectionIds,
            trackEvent
        });

        expect(trackEvent).toHaveBeenCalledWith('grid_filter_toggled', {
            collection_id: 'col-1',
            filter_type: 'annotation_source',
            filter_value: 'Dogs',
            action: 'selected',
            active_count: 2
        });
    });

    it('does not fire trackEvent when the changed id is not found in items', () => {
        const setSelectedCollectionIds = vi.fn();
        const trackEvent = vi.fn();

        handleAnnotationSourceFilterChange({
            newIds: ['c2'],
            prevIds: ['unknown', 'c2'],
            items,
            collectionId: 'col-1',
            setSelectedCollectionIds,
            trackEvent
        });

        expect(setSelectedCollectionIds).toHaveBeenCalledWith(['c2']);
        expect(trackEvent).not.toHaveBeenCalled();
    });

    it('reports active_count as the length of newIds', () => {
        const setSelectedCollectionIds = vi.fn();
        const trackEvent = vi.fn();

        handleAnnotationSourceFilterChange({
            newIds: [],
            prevIds: ['c1'],
            items,
            collectionId: 'col-1',
            setSelectedCollectionIds,
            trackEvent
        });

        expect(trackEvent).toHaveBeenCalledWith('grid_filter_toggled', {
            collection_id: 'col-1',
            filter_type: 'annotation_source',
            filter_value: 'Dogs',
            action: 'unselected',
            active_count: 0
        });
    });
});
