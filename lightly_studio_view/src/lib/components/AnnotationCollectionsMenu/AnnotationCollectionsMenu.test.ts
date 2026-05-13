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
    useAnnotationCollections: vi.fn(() => readable({ data: mocks.collections }))
}));

vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', () => ({
    useAnnotationCollectionsFilter: vi.fn(() => ({
        setSelectedCollectionIds: mocks.setSelectedCollectionIds,
        setCollectionIdToName: mocks.setCollectionIdToName
    }))
}));

describe('AnnotationCollectionsMenu', () => {
    const defaultProps = { collectionId: 'col-1' };

    it('renders nothing when there are no collections', () => {
        mocks.collections = [];
        render(AnnotationCollectionsMenu, defaultProps);
        expect(screen.queryByText('Collections')).not.toBeInTheDocument();
        expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    });

    it('renders a menu item for each collection', () => {
        mocks.collections = [
            { collection_id: 'c1', name: 'Dogs' },
            { collection_id: 'c2', name: 'Cats' }
        ];
        render(AnnotationCollectionsMenu, defaultProps);

        expect(screen.getByText('Dogs')).toBeInTheDocument();
        expect(screen.getByText('Cats')).toBeInTheDocument();
        expect(screen.getAllByRole('checkbox')).toHaveLength(2);
    });

    it('calls setSelectedCollectionIds with the checked id when a collection is selected', async () => {
        mocks.collections = [{ collection_id: 'c1', name: 'Dogs' }];
        render(AnnotationCollectionsMenu, defaultProps);

        await screen.getAllByRole('checkbox')[0].click();

        expect(mocks.setSelectedCollectionIds).toHaveBeenCalledWith(['c1']);
    });

    it('calls setSelectedCollectionIds with empty array when a collection is deselected', async () => {
        mocks.collections = [{ collection_id: 'c1', name: 'Dogs' }];
        render(AnnotationCollectionsMenu, defaultProps);

        const checkbox = screen.getAllByRole('checkbox')[0];
        await checkbox.click();

        expect(mocks.setSelectedCollectionIds).toHaveBeenLastCalledWith([]);
    });
});
