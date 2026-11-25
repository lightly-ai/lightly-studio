import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import {
    getTickDetailsQueryKey,
    readAnnotationLabelsOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import { createAnnotationIdMap } from '../cuboidUndo';
import { useUpdateCuboidClass } from './useUpdateCuboidClass.svelte';

const { updateAnnotations } = vi.hoisted(() => ({ updateAnnotations: vi.fn() }));
const queryClient = new QueryClient();

vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations })
}));
vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    useQueryClient: () => queryClient
}));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

const onUpdated = vi.fn();
const addReversibleAction = vi.fn();
const persistedAnnotation = {
    sample_id: 'annotation-1',
    annotation_label: { annotation_label_name: 'truck' }
} as AnnotationView;
const defaultParams = {
    getCollectionId: () => 'collection-1',
    getDatasetId: () => 'dataset-1',
    getSequenceId: () => 'sequence-1',
    onUpdated,
    getAnnotations: () => [persistedAnnotation],
    annotationIds: createAnnotationIdMap(),
    addReversibleAction
};
const path = { dataset_id: 'dataset-1', sequence_id: 'sequence-1', seq_number: 0 };

describe('useUpdateCuboidClass', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        queryClient.clear();
        updateAnnotations.mockResolvedValue(undefined);
        onUpdated.mockResolvedValue(undefined);
    });

    it('saves the class before refreshing the workspace', async () => {
        let finishSave: () => void = () => {};
        updateAnnotations.mockReturnValue(new Promise<void>((resolve) => (finishSave = resolve)));

        const pending = useUpdateCuboidClass(defaultParams).handleLabelChange(
            'annotation-1',
            'car',
            'annotation-collection-1'
        );

        expect(updateAnnotations).toHaveBeenCalledWith(
            [
                {
                    annotation_id: 'annotation-1',
                    collection_id: 'collection-1',
                    label_name: 'car'
                }
            ],
            'collection-1'
        );
        expect(onUpdated).not.toHaveBeenCalled();
        finishSave();
        await pending;
        expect(onUpdated).toHaveBeenCalledOnce();
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('invalidates every tick and display frame only in the affected dataset and sequence', async () => {
        const affectedKeys = [
            getTickDetailsQueryKey({ path }),
            getTickDetailsQueryKey({ path: { ...path, seq_number: 1 } }),
            getTickDetailsQueryKey({ path, query: { target_frame_id: 'base_link' } })
        ];
        const otherKeys = [
            getTickDetailsQueryKey({ path: { ...path, sequence_id: 'sequence-2' } }),
            getTickDetailsQueryKey({ path: { ...path, dataset_id: 'dataset-2' } })
        ];
        for (const key of [...affectedKeys, ...otherKeys]) {
            queryClient.setQueryData(key, { annotations: [] });
        }

        await useUpdateCuboidClass(defaultParams).handleLabelChange(
            'annotation-1',
            'car',
            'annotation-collection-1'
        );

        for (const key of affectedKeys) {
            expect(queryClient.getQueryState(key)?.isInvalidated).toBe(true);
        }
        for (const key of otherKeys) {
            expect(queryClient.getQueryState(key)?.isInvalidated).toBe(false);
        }
    });

    it('uses the current collection and sequence when the workspace changes', async () => {
        let collectionId = 'collection-1';
        let datasetId = 'dataset-1';
        let sequenceId = 'sequence-1';
        const { handleLabelChange } = useUpdateCuboidClass({
            ...defaultParams,
            getCollectionId: () => collectionId,
            getDatasetId: () => datasetId,
            getSequenceId: () => sequenceId
        });
        collectionId = 'collection-2';
        datasetId = 'dataset-2';
        sequenceId = 'sequence-2';
        const key = getTickDetailsQueryKey({
            path: { dataset_id: datasetId, sequence_id: sequenceId, seq_number: 0 }
        });
        queryClient.setQueryData(key, { annotations: [] });

        await handleLabelChange('annotation-2', 'pedestrian', 'annotation-collection-2');

        expect(updateAnnotations).toHaveBeenCalledWith(
            [
                {
                    annotation_id: 'annotation-2',
                    collection_id: 'collection-2',
                    label_name: 'pedestrian'
                }
            ],
            'collection-2'
        );
        expect(queryClient.getQueryState(key)?.isInvalidated).toBe(true);
    });

    it('invalidates annotation labels for the cuboid annotation collection, not the group collection', async () => {
        const annotationCollectionKey = readAnnotationLabelsOptions({
            path: { collection_id: 'annotation-collection-1' }
        }).queryKey;
        const groupCollectionKey = readAnnotationLabelsOptions({
            path: { collection_id: 'collection-1' }
        }).queryKey;
        queryClient.setQueryData(annotationCollectionKey, []);
        queryClient.setQueryData(groupCollectionKey, []);

        await useUpdateCuboidClass(defaultParams).handleLabelChange(
            'annotation-1',
            'car',
            'annotation-collection-1'
        );

        expect(queryClient.getQueryState(annotationCollectionKey)?.isInvalidated).toBe(true);
        expect(queryClient.getQueryState(groupCollectionKey)?.isInvalidated).toBe(false);
    });

    it('reports a failed save without invalidating cached ticks or refreshing', async () => {
        updateAnnotations.mockRejectedValue(new Error('save failed'));
        const key = getTickDetailsQueryKey({ path });
        queryClient.setQueryData(key, { annotations: [] });

        await expect(
            useUpdateCuboidClass(defaultParams).handleLabelChange(
                'annotation-1',
                'car',
                'annotation-collection-1'
            )
        ).rejects.toThrow('save failed');

        expect(toast.error).toHaveBeenCalledExactlyOnceWith(
            'Failed to update annotation class. Please try again.'
        );
        expect(queryClient.getQueryState(key)?.isInvalidated).toBe(false);
        expect(onUpdated).not.toHaveBeenCalled();
    });

    it('reports a failed refresh after saving the class', async () => {
        onUpdated.mockRejectedValue(new Error('refresh failed'));

        await useUpdateCuboidClass(defaultParams).handleLabelChange(
            'annotation-1',
            'car',
            'annotation-collection-1'
        );

        expect(updateAnnotations).toHaveBeenCalledOnce();
        expect(toast.error).toHaveBeenCalledExactlyOnceWith(
            'Annotation class updated, but the workspace could not refresh. Please try again.'
        );
    });

    describe('undo', () => {
        const changeToCar = (params = defaultParams) =>
            useUpdateCuboidClass(params).handleLabelChange(
                'annotation-1',
                'car',
                'annotation-collection-1'
            );

        it('adds an undo that saves the previous class and refreshes', async () => {
            await changeToCar();
            updateAnnotations.mockClear();
            onUpdated.mockClear();

            await (addReversibleAction.mock.lastCall?.[0] as ReversibleAction).execute();

            expect(updateAnnotations).toHaveBeenCalledExactlyOnceWith(
                [
                    {
                        annotation_id: 'annotation-1',
                        collection_id: 'collection-1',
                        label_name: 'truck'
                    }
                ],
                'collection-1'
            );
            await vi.waitFor(() => expect(onUpdated).toHaveBeenCalledOnce());
        });

        it('saves the previous class for the cuboid that replaced a deleted one', async () => {
            const annotationIds = createAnnotationIdMap();
            await changeToCar({ ...defaultParams, annotationIds });
            annotationIds.replace('annotation-1', 'restored-1');
            updateAnnotations.mockClear();

            await (addReversibleAction.mock.lastCall?.[0] as ReversibleAction).execute();

            expect(updateAnnotations).toHaveBeenCalledWith(
                [expect.objectContaining({ annotation_id: 'restored-1', label_name: 'truck' })],
                'collection-1'
            );
        });

        it('adds no undo when the save fails', async () => {
            updateAnnotations.mockRejectedValue(new Error('save failed'));

            await expect(changeToCar()).rejects.toThrow('save failed');

            expect(addReversibleAction).not.toHaveBeenCalled();
        });

        it('adds no undo when the class does not change', async () => {
            await useUpdateCuboidClass(defaultParams).handleLabelChange(
                'annotation-1',
                'truck',
                'annotation-collection-1'
            );

            expect(addReversibleAction).not.toHaveBeenCalled();
        });

        it('saves the class of the last change when its refresh failed', async () => {
            const { handleLabelChange } = useUpdateCuboidClass(defaultParams);
            onUpdated.mockRejectedValueOnce(new Error('refresh failed'));
            await handleLabelChange('annotation-1', 'car', 'annotation-collection-1');
            await handleLabelChange('annotation-1', 'pedestrian', 'annotation-collection-1');
            updateAnnotations.mockClear();

            await (addReversibleAction.mock.lastCall?.[0] as ReversibleAction).execute();

            expect(updateAnnotations).toHaveBeenCalledWith(
                [expect.objectContaining({ annotation_id: 'annotation-1', label_name: 'car' })],
                'collection-1'
            );
        });

        it('saves the previous class in the collection of the change', async () => {
            let collectionId = 'collection-1';
            await changeToCar({ ...defaultParams, getCollectionId: () => collectionId });
            collectionId = 'collection-2';
            updateAnnotations.mockClear();

            await (addReversibleAction.mock.lastCall?.[0] as ReversibleAction).execute();

            expect(updateAnnotations).toHaveBeenCalledWith(
                [expect.objectContaining({ collection_id: 'collection-1' })],
                'collection-1'
            );
        });
    });
});
