import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import { createAnnotationIdMap } from '../cuboidUndo';
import { useUpdateCuboidAnnotation } from './useUpdateCuboidAnnotation.svelte';

const { updateAnnotations } = vi.hoisted(() => ({ updateAnnotations: vi.fn() }));

vi.mock('$lib/hooks', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations })
}));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

type Transform = Parameters<
    ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform']
>[0];

const transform: Transform = {
    annotationId: 'annotation-1',
    frameId: 'lidar-front',
    center: [2, -3, 4],
    rotation: [0, 0, 0.6, 0.8],
    size: [5, 6, 7]
};

const previousCuboid = {
    frame_id: 'lidar-front',
    px: 0,
    py: 0,
    pz: 0,
    qx: 0,
    qy: 0,
    qz: 0,
    qw: 1,
    sx: 1,
    sy: 1,
    sz: 1,
    interpolated: true
};

const persistedAnnotation = {
    sample_id: 'annotation-1',
    cuboid_3d_details: previousCuboid
} as AnnotationView;

describe('useUpdateCuboidAnnotation', () => {
    const onUpdated = vi.fn();
    const addReversibleAction = vi.fn();
    const onRestore = vi.fn();
    let defaultParams: Parameters<typeof useUpdateCuboidAnnotation>[0];

    beforeEach(() => {
        defaultParams = {
            getCollectionId: () => 'collection-1',
            onUpdated,
            getAnnotations: () => [persistedAnnotation],
            annotationIds: createAnnotationIdMap(),
            addReversibleAction,
            onRestore
        };
    });

    beforeEach(() => {
        vi.resetAllMocks();
        updateAnnotations.mockResolvedValue(undefined);
        onUpdated.mockResolvedValue(undefined);
    });

    it('saves the transformed geometry before refreshing annotations', async () => {
        let finishSave: () => void = () => {};
        updateAnnotations.mockReturnValue(new Promise<void>((resolve) => (finishSave = resolve)));
        const pending = useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);

        await Promise.resolve(); // let the serialization chain start the save
        expect(updateAnnotations).toHaveBeenCalledWith(
            [
                {
                    annotation_id: 'annotation-1',
                    collection_id: 'collection-1',
                    cuboid_3d: {
                        frame_id: 'lidar-front',
                        px: 2,
                        py: -3,
                        pz: 4,
                        qx: 0,
                        qy: 0,
                        qz: 0.6,
                        qw: 0.8,
                        sx: 5,
                        sy: 6,
                        sz: 7
                    }
                }
            ],
            'collection-1'
        );
        expect(onUpdated).not.toHaveBeenCalled();
        finishSave();
        expect(await pending).toBe(true);
        expect(onUpdated).toHaveBeenCalledOnce();
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('uses the current annotation source when saving', async () => {
        let collectionId = 'collection-1';
        const { handleCuboidTransform } = useUpdateCuboidAnnotation({
            ...defaultParams,
            getCollectionId: () => collectionId
        });
        collectionId = 'collection-2';

        await handleCuboidTransform(transform);

        expect(updateAnnotations).toHaveBeenCalledWith(
            [expect.objectContaining({ collection_id: 'collection-2' })],
            'collection-2'
        );
    });

    it('does not save or refresh without an annotation source', async () => {
        const result = await useUpdateCuboidAnnotation({
            ...defaultParams,
            getCollectionId: () => undefined
        }).handleCuboidTransform(transform);

        expect(result).toBe(false);
        expect(updateAnnotations).not.toHaveBeenCalled();
        expect(onUpdated).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('reports a failed save and refetches to restore the cuboid', async () => {
        updateAnnotations.mockRejectedValue(new Error('save failed'));

        const result =
            await useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith('Failed to update annotation. Please try again.');
        // Refetch is triggered even on failure so the viewport reverts to persisted geometry.
        expect(onUpdated).toHaveBeenCalledOnce();
        expect(toast.error).toHaveBeenCalledOnce();
    });

    it('serializes concurrent saves for the same cuboid', async () => {
        let finishFirstSave!: () => void;
        const order: string[] = [];

        updateAnnotations
            .mockImplementationOnce(() => {
                order.push('start-1');
                return new Promise<void>((resolve) => (finishFirstSave = resolve));
            })
            .mockImplementation(() => {
                order.push('start-2');
                return Promise.resolve();
            });

        const { handleCuboidTransform } = useUpdateCuboidAnnotation(defaultParams);
        const first = handleCuboidTransform(transform);
        const second = handleCuboidTransform(transform);

        await Promise.resolve(); // let the first save start
        expect(order).toEqual(['start-1']);

        finishFirstSave();
        await Promise.all([first, second]);

        expect(order).toEqual(['start-1', 'start-2']);
    });

    it('returns true even when the refresh fails after a successful save', async () => {
        onUpdated.mockRejectedValue(new Error('refresh failed'));

        const result =
            await useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);

        expect(result).toBe(true);
        expect(updateAnnotations).toHaveBeenCalledOnce();
        expect(toast.error).toHaveBeenCalledExactlyOnceWith(
            'Annotation updated, but the workspace could not refresh. Please try again.'
        );
    });

    describe('undo', () => {
        const lastUndo = () => addReversibleAction.mock.lastCall?.[0] as ReversibleAction;

        it('adds an undo with the previous geometry and interpolation after a save', async () => {
            await useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);
            updateAnnotations.mockClear();

            expect(addReversibleAction).toHaveBeenCalledOnce();
            await lastUndo().execute();

            expect(updateAnnotations).toHaveBeenCalledExactlyOnceWith(
                [
                    {
                        annotation_id: 'annotation-1',
                        collection_id: 'collection-1',
                        cuboid_3d: previousCuboid
                    }
                ],
                'collection-1'
            );
            expect(onRestore).toHaveBeenCalledWith('annotation-1');
            expect(addReversibleAction).toHaveBeenCalledOnce();
        });

        it('adds no undo when the save fails', async () => {
            updateAnnotations.mockRejectedValue(new Error('save failed'));

            await useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);

            expect(addReversibleAction).not.toHaveBeenCalled();
        });

        it('adds no undo when the previous geometry is unknown', async () => {
            await useUpdateCuboidAnnotation({
                ...defaultParams,
                getAnnotations: () => []
            }).handleCuboidTransform(transform);

            expect(addReversibleAction).not.toHaveBeenCalled();
        });

        it('restores the cuboid that replaced a deleted one', async () => {
            await useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);
            defaultParams.annotationIds.replace('annotation-1', 'restored-1');
            updateAnnotations.mockClear();

            await lastUndo().execute();

            expect(updateAnnotations).toHaveBeenCalledWith(
                [expect.objectContaining({ annotation_id: 'restored-1' })],
                'collection-1'
            );
            expect(onRestore).toHaveBeenCalledWith('restored-1');
        });

        it('restores after a save of the same cuboid that still runs', async () => {
            const { handleCuboidTransform } = useUpdateCuboidAnnotation(defaultParams);
            await handleCuboidTransform(transform);
            const undo = lastUndo();
            let finishSave!: () => void;
            updateAnnotations.mockClear();
            updateAnnotations.mockImplementationOnce(
                () => new Promise<void>((resolve) => (finishSave = resolve))
            );
            void handleCuboidTransform(transform);
            await Promise.resolve();

            const restoring = undo.execute();
            await Promise.resolve();
            expect(updateAnnotations).toHaveBeenCalledOnce();
            finishSave();
            await restoring;

            expect(updateAnnotations).toHaveBeenCalledTimes(2);
        });

        it('restores the geometry of the last save when its refresh failed', async () => {
            const { handleCuboidTransform } = useUpdateCuboidAnnotation(defaultParams);
            onUpdated.mockRejectedValueOnce(new Error('refresh failed'));
            await handleCuboidTransform(transform);
            await handleCuboidTransform({ ...transform, center: [9, 9, 9] });
            updateAnnotations.mockClear();

            await lastUndo().execute();

            expect(updateAnnotations).toHaveBeenCalledWith(
                [
                    expect.objectContaining({
                        cuboid_3d: expect.objectContaining({ px: 2, py: -3, pz: 4 })
                    })
                ],
                'collection-1'
            );
        });

        it('restores in the collection of the save after the collection changes', async () => {
            let collectionId = 'collection-1';
            await useUpdateCuboidAnnotation({
                ...defaultParams,
                getCollectionId: () => collectionId
            }).handleCuboidTransform(transform);
            collectionId = 'collection-2';
            updateAnnotations.mockClear();

            await lastUndo().execute();

            expect(updateAnnotations).toHaveBeenCalledWith(
                [expect.objectContaining({ collection_id: 'collection-1' })],
                'collection-1'
            );
        });

        it('rejects the undo when the restore fails', async () => {
            await useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);
            updateAnnotations.mockRejectedValue(new Error('save failed'));

            await expect(lastUndo().execute()).rejects.toThrow();
        });
    });

    it('waits for the running saves of a cuboid', async () => {
        let finishSave!: () => void;
        updateAnnotations.mockReturnValue(new Promise<void>((resolve) => (finishSave = resolve)));
        const { handleCuboidTransform, waitForSaves } = useUpdateCuboidAnnotation(defaultParams);
        void handleCuboidTransform(transform);
        let isWaiting = true;

        const waiting = waitForSaves('annotation-1').then(() => (isWaiting = false));
        await Promise.resolve();
        expect(isWaiting).toBe(true);
        finishSave();
        await waiting;

        expect(isWaiting).toBe(false);
    });
});
