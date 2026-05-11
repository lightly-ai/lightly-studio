import { describe, it, expect, vi, beforeEach } from 'vitest';
import { writable, get } from 'svelte/store';
import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery } from '@tanstack/svelte-query';

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    readAnnotationCollectionsOptions: vi.fn((config) => ({
        queryKey: ['annotationCollections', config.path.collection_id],
        ...config
    }))
}));

vi.mock('@tanstack/svelte-query', () => ({
    createQuery: vi.fn()
}));

import { useAnnotationCollections } from './useAnnotationCollections';

describe('useAnnotationCollections', () => {
    const mockAnnotationCollections: AnnotationCollectionView[] = [
        { collection_id: 'ac-1', name: 'Collection A' },
        { collection_id: 'ac-2', name: 'Collection B' }
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('calls createQuery with the correct path parameter', () => {
        const mockStore = writable({ data: mockAnnotationCollections, error: null, isLoading: false });
        vi.mocked(createQuery).mockReturnValue(
            mockStore as unknown as ReturnType<typeof createQuery>
        );

        useAnnotationCollections({ collectionId: 'collection-1' });

        expect(createQuery).toHaveBeenCalledWith(
            expect.objectContaining({
                path: { collection_id: 'collection-1' }
            })
        );
    });

    it('returns the query store from createQuery', () => {
        const mockStore = writable({ data: mockAnnotationCollections, error: null, isLoading: false });
        vi.mocked(createQuery).mockReturnValue(
            mockStore as unknown as ReturnType<typeof createQuery>
        );

        const result = useAnnotationCollections({ collectionId: 'collection-1' });

        expect(get(result).data).toEqual(mockAnnotationCollections);
    });

    it('reflects loading state', () => {
        const mockStore = writable({ data: undefined, error: null, isLoading: true });
        vi.mocked(createQuery).mockReturnValue(
            mockStore as unknown as ReturnType<typeof createQuery>
        );

        const result = useAnnotationCollections({ collectionId: 'collection-1' });

        expect(get(result).isLoading).toBe(true);
        expect(get(result).data).toBeUndefined();
    });

    it('reflects error state', () => {
        const mockError = new Error('Failed to fetch annotation collections');
        const mockStore = writable({ data: undefined, error: mockError, isLoading: false });
        vi.mocked(createQuery).mockReturnValue(
            mockStore as unknown as ReturnType<typeof createQuery>
        );

        const result = useAnnotationCollections({ collectionId: 'collection-1' });

        expect(get(result).error).toEqual(mockError);
    });
});
