import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import AnnotationCollectionsMenu from './AnnotationCollectionsMenu.svelte';

const mocks = vi.hoisted(() => ({
    collections: [] as { collection_id: string; name: string }[],
    setSelectedCollectionIds: vi.fn(),
    setCollectionIdToName: vi.fn()
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: vi.fn(() => ({ data: mocks.collections }))
}));

vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', () => ({
    useAnnotationCollectionsFilter: vi.fn(() => ({
        setSelectedCollectionIds: mocks.setSelectedCollectionIds,
        setCollectionIdToName: mocks.setCollectionIdToName,
        selectedCollectionIds: readable([] as string[])
    }))
}));

describe('AnnotationCollectionsMenu', () => {
    const defaultProps = { collectionId: 'col-1' };

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

    it('does not initialize the annotation source filter when there is only one collection', () => {
        mocks.collections = [{ collection_id: 'c1', name: 'Ground Truth' }];
        render(AnnotationCollectionsMenu, defaultProps);
        expect(mocks.setSelectedCollectionIds).not.toHaveBeenCalled();
        expect(mocks.setCollectionIdToName).not.toHaveBeenCalled();
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
        render(AnnotationCollectionsMenu, defaultProps);

        await screen.getAllByRole('checkbox')[0].click();

        expect(mocks.setSelectedCollectionIds).toHaveBeenLastCalledWith(['c2']);
    });

    it('calls setSelectedCollectionIds with empty array when all collections are deselected', async () => {
        mocks.collections = [
            { collection_id: 'c1', name: 'Dogs' },
            { collection_id: 'c2', name: 'Cats' }
        ];
        render(AnnotationCollectionsMenu, defaultProps);

        const [first, second] = screen.getAllByRole('checkbox');
        await first.click();
        await second.click();

        expect(mocks.setSelectedCollectionIds).toHaveBeenLastCalledWith([]);
    });
});
