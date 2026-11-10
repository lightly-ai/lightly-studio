import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useMoveAnnotationByCopy } from './useMoveAnnotationByCopy.svelte';

const mocks = vi.hoisted(() => ({
    create: vi.fn(),
    remove: vi.fn(),
    error: vi.fn(),
    labels: undefined as
        | { annotation_label_name: string; annotation_label_id: string }[]
        | undefined
}));
vi.mock('$lib/hooks', () => ({
    useAnnotationLabels: () => ({
        get data() {
            return mocks.labels;
        }
    }),
    useCreateAnnotation: () => ({ createAnnotation: mocks.create }),
    useDeleteAnnotation: () => ({ deleteAnnotation: mocks.remove })
}));
vi.mock('svelte-sonner', () => ({ toast: { error: mocks.error } }));

const bounds = { x: 1, y: 2, width: 3, height: 4 };
const box: AnnotationView = {
    sample_id: 'original',
    parent_sample_id: 'image',
    annotation_collection_id: 'predictions',
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'car' },
    confidence: 0.9,
    object_detection_details: bounds,
    created_at: new Date()
};

describe('useMoveAnnotationByCopy', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        mocks.labels = [{ annotation_label_name: 'car', annotation_label_id: 'class' }];
        mocks.remove.mockResolvedValue(undefined);
    });

    const moves = useMoveAnnotationByCopy(() => 'images');
    const { moveByCopy } = moves;
    const isMoving = () => moves.isMoving;

    it('copies the box into the source, then deletes the original', async () => {
        mocks.create.mockResolvedValue({ sample_id: 'copy' });

        expect(await moveByCopy(box, 'gt')).toBe('copy');

        expect(mocks.create).toHaveBeenCalledWith({
            annotation_label_id: 'class',
            annotation_type: 'object_detection',
            annotation_collection_name: 'gt',
            parent_sample_id: 'image',
            ...bounds
        });
        expect(mocks.remove).toHaveBeenCalledWith('original', 'object_detection');
        expect(mocks.create.mock.invocationCallOrder[0]).toBeLessThan(
            mocks.remove.mock.invocationCallOrder[0]
        );
    });

    it('keeps the segmentation mask', async () => {
        mocks.create.mockResolvedValue({ sample_id: 'copy' });
        const mask: AnnotationView = {
            ...box,
            annotation_type: 'segmentation_mask',
            object_detection_details: undefined,
            segmentation_details: { ...bounds, segmentation_mask: [0, 2, 3] }
        };

        await moveByCopy(mask, 'gt');

        expect(mocks.create).toHaveBeenCalledWith(
            expect.objectContaining({
                annotation_type: 'segmentation_mask',
                ...bounds,
                segmentation_mask: [0, 2, 3]
            })
        );
    });

    it('deletes nothing when the copy fails', async () => {
        mocks.create.mockRejectedValue(new Error('offline'));

        expect(await moveByCopy(box, 'gt')).toBeNull();

        expect(mocks.remove).not.toHaveBeenCalled();
        expect(mocks.error).toHaveBeenCalledExactlyOnceWith(
            'Could not move the annotation. Please try again.'
        );
    });

    it('keeps the copy when the original cannot be deleted', async () => {
        mocks.create.mockResolvedValue({ sample_id: 'copy' });
        mocks.remove.mockRejectedValue(new Error('offline'));

        expect(await moveByCopy(box, 'gt')).toBe('copy');

        expect(mocks.error).toHaveBeenCalledExactlyOnceWith(
            'Copied to gt, but the original is still there.'
        );
    });

    it('moves once while a move is in flight', async () => {
        let finishCopy!: (value: { sample_id: string }) => void;
        mocks.create.mockReturnValue(new Promise((resolve) => (finishCopy = resolve)));

        const first = moveByCopy(box, 'gt');
        const second = moveByCopy(box, 'gt');
        expect(isMoving()).toBe(true);
        finishCopy({ sample_id: 'copy' });

        expect(await second).toBeNull();
        expect(await first).toBe('copy');
        expect(mocks.create).toHaveBeenCalledOnce();
        expect(mocks.remove).toHaveBeenCalledOnce();
        expect(isMoving()).toBe(false);
    });

    it('copies nothing while the classes load', async () => {
        mocks.labels = undefined;

        expect(await moveByCopy(box, 'gt')).toBeNull();

        expect(mocks.create).not.toHaveBeenCalled();
        expect(mocks.remove).not.toHaveBeenCalled();
    });
});
