import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
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

describe('useUpdateCuboidAnnotation', () => {
    const onUpdated = vi.fn();
    const defaultParams: Parameters<typeof useUpdateCuboidAnnotation>[0] = {
        getCollectionId: () => 'collection-1',
        onUpdated
    };

    beforeEach(() => {
        vi.resetAllMocks();
        updateAnnotations.mockResolvedValue(undefined);
        onUpdated.mockResolvedValue(undefined);
    });

    it('saves the transformed geometry before refreshing annotations', async () => {
        let finishSave: () => void = () => {};
        updateAnnotations.mockReturnValue(new Promise<void>((resolve) => (finishSave = resolve)));
        const pending = useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);

        expect(updateAnnotations).toHaveBeenCalledWith([
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
        ]);
        expect(onUpdated).not.toHaveBeenCalled();
        finishSave();
        await pending;
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

        expect(updateAnnotations).toHaveBeenCalledWith([
            expect.objectContaining({ collection_id: 'collection-2' })
        ]);
    });

    it('does not save or refresh without an annotation source', async () => {
        await useUpdateCuboidAnnotation({
            ...defaultParams,
            getCollectionId: () => undefined
        }).handleCuboidTransform(transform);

        expect(updateAnnotations).not.toHaveBeenCalled();
        expect(onUpdated).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('reports a failed save without refreshing annotations', async () => {
        updateAnnotations.mockRejectedValue(new Error('save failed'));

        await useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);

        expect(toast.error).toHaveBeenCalledWith('Failed to update annotation. Please try again.');
        expect(onUpdated).not.toHaveBeenCalled();
    });

    it('distinguishes a refresh failure from a failed save', async () => {
        onUpdated.mockRejectedValue(new Error('refresh failed'));

        await useUpdateCuboidAnnotation(defaultParams).handleCuboidTransform(transform);

        expect(updateAnnotations).toHaveBeenCalledOnce();
        expect(toast.error).toHaveBeenCalledExactlyOnceWith(
            'Annotation updated, but the workspace could not refresh. Please try again.'
        );
    });
});
