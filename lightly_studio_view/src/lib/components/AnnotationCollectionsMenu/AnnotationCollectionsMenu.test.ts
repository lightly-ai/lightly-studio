import { render, screen } from '@testing-library/svelte';
import { type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AnnotationCollectionsMenu from './AnnotationCollectionsMenu.svelte';

const mocks = vi.hoisted(() => ({
    collections: [] as { collection_id: string; name: string }[],
    selectedCollectionIds: null as unknown as Writable<string[]>,
    setSelectedCollectionIds: vi.fn(),
    seedSelectionIfNeeded: vi.fn()
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: vi.fn(() => ({ data: mocks.collections }))
}));

vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', async () => {
    const { writable } = await import('svelte/store');
    // A real writable backs the store so the controlled checkboxes reflect intermediate
    // state across consecutive toggles.
    mocks.selectedCollectionIds = writable<string[]>([]);
    mocks.setSelectedCollectionIds = vi.fn((ids: string[]) => mocks.selectedCollectionIds.set(ids));
    return {
        useAnnotationCollectionsFilter: vi.fn(() => ({
            selectedCollectionIds: mocks.selectedCollectionIds,
            setSelectedCollectionIds: mocks.setSelectedCollectionIds,
            seedSelectionIfNeeded: mocks.seedSelectionIfNeeded
        }))
    };
});

describe('AnnotationCollectionsMenu', () => {
    const defaultProps = { collectionId: 'col-1' };

    beforeEach(() => {
        vi.clearAllMocks();
        mocks.collections = [];
        mocks.selectedCollectionIds.set([]);
    });

    it('renders nothing when there are no collections', () => {
        mocks.collections = [];
        render(AnnotationCollectionsMenu, defaultProps);
        expect(screen.queryByText('Annotation Sources')).not.toBeInTheDocument();
        expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    });

    it('renders nothing when there is only one collection', () => {
        mocks.collections = [{ collection_id: 'c1', name: 'Ground Truth' }];
        render(AnnotationCollectionsMenu, defaultProps);
        expect(screen.queryByText('Annotation Sources')).not.toBeInTheDocument();
        expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    });

    it('does not seed the annotation source filter when there is only one collection', () => {
        mocks.collections = [{ collection_id: 'c1', name: 'Ground Truth' }];
        render(AnnotationCollectionsMenu, defaultProps);
        expect(mocks.seedSelectionIfNeeded).not.toHaveBeenCalled();
    });

    it('seeds the annotation source filter with all collections when there are two or more', () => {
        mocks.collections = [
            { collection_id: 'c1', name: 'Dogs' },
            { collection_id: 'c2', name: 'Cats' }
        ];
        render(AnnotationCollectionsMenu, defaultProps);

        expect(mocks.seedSelectionIfNeeded).toHaveBeenCalledWith('col-1', [
            { id: 'c1', name: 'Dogs' },
            { id: 'c2', name: 'Cats' }
        ]);
    });

    it('renders a menu item for each collection when there are two or more', () => {
        mocks.collections = [
            { collection_id: 'c1', name: 'Dogs' },
            { collection_id: 'c2', name: 'Cats' }
        ];
        render(AnnotationCollectionsMenu, defaultProps);

        expect(screen.getByText('Dogs')).toBeInTheDocument();
        expect(screen.getByText('Cats')).toBeInTheDocument();
        expect(screen.getAllByRole('checkbox')).toHaveLength(2);
    });

    it('calls setSelectedCollectionIds with the remaining ids when a collection is deselected', async () => {
        mocks.collections = [
            { collection_id: 'c1', name: 'Dogs' },
            { collection_id: 'c2', name: 'Cats' }
        ];
        mocks.selectedCollectionIds.set(['c1', 'c2']);
        render(AnnotationCollectionsMenu, defaultProps);

        await screen.getAllByRole('checkbox')[0].click();

        expect(mocks.setSelectedCollectionIds).toHaveBeenLastCalledWith(['c2']);
    });

    it('calls setSelectedCollectionIds with empty array when all collections are deselected', async () => {
        mocks.collections = [
            { collection_id: 'c1', name: 'Dogs' },
            { collection_id: 'c2', name: 'Cats' }
        ];
        mocks.selectedCollectionIds.set(['c1', 'c2']);
        render(AnnotationCollectionsMenu, defaultProps);

        const [first, second] = screen.getAllByRole('checkbox');
        await first.click();
        await second.click();

        expect(mocks.setSelectedCollectionIds).toHaveBeenLastCalledWith([]);
    });
});
