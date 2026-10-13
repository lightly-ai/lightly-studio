import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { useCreateCuboidAnnotation } from './useCreateCuboidAnnotation.svelte';
type Params = Parameters<typeof useCreateCuboidAnnotation>[0];

const {
    createAnnotation,
    createLabel,
    handleCancel,
    handleConfirm,
    requestLabel,
    updateLastAnnotationLabel,
    useAnnotationLabels,
    useCreateAnnotation,
    useCreateLabel,
    useGlobalStorage
} = vi.hoisted(() => ({
    createAnnotation: vi.fn(),
    createLabel: vi.fn(),
    handleCancel: vi.fn(),
    handleConfirm: vi.fn(),
    requestLabel: vi.fn(),
    updateLastAnnotationLabel: vi.fn(),
    useAnnotationLabels: vi.fn(),
    useCreateAnnotation: vi.fn(),
    useCreateLabel: vi.fn(),
    useGlobalStorage: vi.fn()
}));

vi.mock('$lib/hooks', async () => {
    const { writable } = await import('svelte/store');
    return {
        useAnnotationLabels,
        useCreateAnnotation,
        useCreateLabel,
        useGlobalStorage,
        useSelectClassDialog: () => ({
            open: writable(false),
            requestLabel,
            handleConfirm,
            handleCancel
        })
    };
});

vi.mock('svelte-sonner', () => ({
    toast: { error: vi.fn(), success: vi.fn() }
}));

describe('useCreateCuboidAnnotation', () => {
    const lastAnnotationLabel = writable<Record<string, string>>({});
    const labels = { data: [] as { annotation_label_name: string; annotation_label_id: string }[] };
    const params: Params = {
        getCollectionId: () => 'collection-1',
        getDatasetId: () => 'dataset-1',
        getTickSampleId: () => 'sample-1',
        getSceneFrame: () => ({
            bounds: { min: [0, 0, 0], max: [10, 10, 10] },
            frameId: 'lidar-front'
        })
    };

    beforeEach(() => {
        vi.clearAllMocks();
        lastAnnotationLabel.set({});
        labels.data = [];
        createLabel.mockResolvedValue({ annotation_label_id: 'new-label' });
        createAnnotation.mockResolvedValue({ sample_id: 'annotation-1' });
        requestLabel.mockResolvedValue({ label: 'car' });
        useAnnotationLabels.mockReturnValue(labels);
        useCreateAnnotation.mockReturnValue({ createAnnotation });
        useCreateLabel.mockReturnValue({ createLabel });
        useGlobalStorage.mockReturnValue({ lastAnnotationLabel, updateLastAnnotationLabel });
    });

    it('creates a cuboid with the remembered class and scene frame geometry', async () => {
        lastAnnotationLabel.set({ 'collection-1': 'car' });
        labels.data = [{ annotation_label_name: 'car', annotation_label_id: 'label-1' }];
        const onCreated = vi.fn();

        await useCreateCuboidAnnotation(params).handleCreateCuboid([2, 3, 4], onCreated);

        expect(requestLabel).not.toHaveBeenCalled();
        expect(createLabel).not.toHaveBeenCalled();
        expect(createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({
                parent_sample_id: 'sample-1',
                annotation_type: 'cuboid_3d',
                annotation_label_id: 'label-1',
                cuboid_3d: expect.objectContaining({
                    frame_id: 'lidar-front',
                    px: 2,
                    py: 3,
                    pz: expect.closeTo(4 + Math.sqrt(300) * 0.01),
                    sx: expect.closeTo(Math.sqrt(300) * 0.02),
                    sy: expect.closeTo(Math.sqrt(300) * 0.02),
                    sz: expect.closeTo(Math.sqrt(300) * 0.02)
                })
            })
        );
        expect(onCreated).toHaveBeenCalledWith('annotation-1');
        expect(toast.success).toHaveBeenCalledWith('Annotation created successfully');
    });

    it('asks for a class, creates it, and remembers the selection', async () => {
        const onCreated = vi.fn();

        await useCreateCuboidAnnotation(params).handleCreateCuboid([0, 0, 0], onCreated);

        expect(requestLabel).toHaveBeenCalledOnce();
        expect(createLabel).toHaveBeenCalledWith({
            dataset_id: 'dataset-1',
            annotation_label_name: 'car'
        });
        expect(updateLastAnnotationLabel).toHaveBeenCalledWith('collection-1', 'car');
        expect(createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({ annotation_label_id: 'new-label' })
        );
        expect(onCreated).toHaveBeenCalledWith('annotation-1');
    });

    it('does nothing when the current collection or sample is unavailable', async () => {
        await useCreateCuboidAnnotation({
            ...params,
            getCollectionId: () => undefined
        }).handleCreateCuboid([0, 0, 0], vi.fn());
        await useCreateCuboidAnnotation({
            ...params,
            getTickSampleId: () => undefined
        }).handleCreateCuboid([0, 0, 0], vi.fn());

        expect(requestLabel).not.toHaveBeenCalled();
        expect(createLabel).not.toHaveBeenCalled();
        expect(createAnnotation).not.toHaveBeenCalled();
    });

    it('does not create an annotation when class selection is cancelled', async () => {
        requestLabel.mockResolvedValue(null);

        await useCreateCuboidAnnotation(params).handleCreateCuboid([0, 0, 0], vi.fn());

        expect(createLabel).not.toHaveBeenCalled();
        expect(createAnnotation).not.toHaveBeenCalled();
        expect(updateLastAnnotationLabel).not.toHaveBeenCalled();
    });

    it('shows an error when creating the annotation class fails', async () => {
        createLabel.mockRejectedValue(new Error('request failed'));

        await useCreateCuboidAnnotation(params).handleCreateCuboid([0, 0, 0], vi.fn());

        expect(toast.error).toHaveBeenCalledWith(
            'Failed to create annotation class. Please try again.'
        );
        expect(createAnnotation).not.toHaveBeenCalled();
    });

    it('shows an error when creating the cuboid fails', async () => {
        lastAnnotationLabel.set({ 'collection-1': 'car' });
        labels.data = [{ annotation_label_name: 'car', annotation_label_id: 'label-1' }];
        createAnnotation.mockRejectedValue(new Error('request failed'));

        await useCreateCuboidAnnotation(params).handleCreateCuboid([0, 0, 0], vi.fn());

        expect(toast.error).toHaveBeenCalledWith('Failed to create annotation. Please try again.');
    });

    it('reports refresh failure after saving the annotation', async () => {
        lastAnnotationLabel.set({ 'collection-1': 'car' });
        labels.data = [{ annotation_label_name: 'car', annotation_label_id: 'label-1' }];
        const onCreated = vi.fn().mockRejectedValue(new Error('refresh failed'));

        await useCreateCuboidAnnotation(params).handleCreateCuboid([0, 0, 0], onCreated);

        expect(createAnnotation).toHaveBeenCalledOnce();
        expect(onCreated).toHaveBeenCalledWith('annotation-1');
        expect(toast.error).toHaveBeenCalledWith(
            'Annotation created, but the workspace could not refresh. Please try again.'
        );
    });
});
