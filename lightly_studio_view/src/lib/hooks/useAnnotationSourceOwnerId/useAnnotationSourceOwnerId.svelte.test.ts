import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnnotationSourceOwnerId } from './useAnnotationSourceOwnerId.svelte';

const mocks = vi.hoisted(() => ({
    data: undefined as
        | { collection_id: string; sample_type: string; parent_collection_id?: string | null }
        | undefined
}));

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    createQuery: () => ({
        get data() {
            return mocks.data;
        }
    })
}));

describe('useAnnotationSourceOwnerId', () => {
    beforeEach(() => {
        mocks.data = undefined;
    });

    it('is undefined while the collection loads', () => {
        expect(useAnnotationSourceOwnerId(() => 'c1').ownerCollectionId).toBeUndefined();
    });

    it('is the collection itself outside the annotations grid', () => {
        mocks.data = { collection_id: 'images-1', sample_type: 'image' };

        expect(useAnnotationSourceOwnerId(() => 'images-1').ownerCollectionId).toBe('images-1');
    });

    it('is the parent of an annotation source', () => {
        mocks.data = {
            collection_id: 'source-1',
            sample_type: 'annotation',
            parent_collection_id: 'images-1'
        };

        expect(useAnnotationSourceOwnerId(() => 'source-1').ownerCollectionId).toBe('images-1');
    });
});
