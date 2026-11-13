import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnnotationSourceOwnerId } from './useAnnotationSourceOwnerId.svelte';

const mocks = vi.hoisted(() => ({
    data: undefined as
        | { collection_id: string; sample_type: string; parent_collection_id?: string | null }
        | undefined,
    isError: false,
    hierarchy: undefined as
        | { collection_id: string; sample_type: string; parent_collection_id?: string | null }[]
        | undefined,
    hierarchyIsError: false
}));

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    createQuery: (getOptions: () => { queryKey: [{ _id: string }] }) => {
        const isHierarchy = getOptions().queryKey[0]._id === 'readCollectionHierarchy';
        return {
            get data() {
                return isHierarchy ? mocks.hierarchy : mocks.data;
            },
            get isError() {
                return isHierarchy ? mocks.hierarchyIsError : mocks.isError;
            }
        };
    }
}));

describe('useAnnotationSourceOwnerId', () => {
    beforeEach(() => {
        mocks.data = undefined;
        mocks.isError = false;
        mocks.hierarchy = undefined;
        mocks.hierarchyIsError = false;
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

    it('is the GROUP child of a point-cloud sequence', () => {
        mocks.data = { collection_id: 'sequence-1', sample_type: 'sequence' };
        mocks.hierarchy = [
            { collection_id: 'sequence-1', sample_type: 'sequence' },
            { collection_id: 'group-2', sample_type: 'group', parent_collection_id: 'sequence-2' },
            { collection_id: 'group-1', sample_type: 'group', parent_collection_id: 'sequence-1' }
        ];

        expect(useAnnotationSourceOwnerId(() => 'sequence-1').ownerCollectionId).toBe('group-1');
    });

    it('is undefined while the hierarchy of a sequence loads', () => {
        mocks.data = { collection_id: 'sequence-1', sample_type: 'sequence' };

        expect(useAnnotationSourceOwnerId(() => 'sequence-1').ownerCollectionId).toBeUndefined();
    });

    it('is the VIDEO_FRAME child of a video collection', () => {
        mocks.data = { collection_id: 'videos-1', sample_type: 'video' };
        mocks.hierarchy = [
            { collection_id: 'videos-1', sample_type: 'video' },
            {
                collection_id: 'frames-2',
                sample_type: 'video_frame',
                parent_collection_id: 'videos-2'
            },
            {
                collection_id: 'frames-1',
                sample_type: 'video_frame',
                parent_collection_id: 'videos-1'
            }
        ];

        expect(useAnnotationSourceOwnerId(() => 'videos-1').ownerCollectionId).toBe('frames-1');
    });

    it('is the frame collection itself on the frames grid', () => {
        mocks.data = { collection_id: 'frames-1', sample_type: 'video_frame' };

        expect(useAnnotationSourceOwnerId(() => 'frames-1').ownerCollectionId).toBe('frames-1');
    });

    it('is the sequence itself when it has no GROUP child', () => {
        mocks.data = { collection_id: 'sequence-1', sample_type: 'sequence' };
        mocks.hierarchy = [{ collection_id: 'sequence-1', sample_type: 'sequence' }];

        expect(useAnnotationSourceOwnerId(() => 'sequence-1').ownerCollectionId).toBe('sequence-1');
    });

    it('reports a failed hierarchy query', () => {
        mocks.data = { collection_id: 'sequence-1', sample_type: 'sequence' };
        mocks.hierarchyIsError = true;

        expect(useAnnotationSourceOwnerId(() => 'sequence-1').isError).toBe(true);
    });

    it('reports a failed collection query', () => {
        mocks.isError = true;

        const owner = useAnnotationSourceOwnerId(() => 'c1');

        expect(owner.isError).toBe(true);
        expect(owner.ownerCollectionId).toBeUndefined();
    });
});
