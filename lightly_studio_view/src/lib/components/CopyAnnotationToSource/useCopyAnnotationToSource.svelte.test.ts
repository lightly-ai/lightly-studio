import { expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useCopyAnnotationToSource } from './useCopyAnnotationToSource.svelte';

const mocks = vi.hoisted(() => ({
    create: vi.fn(),
    remove: vi.fn(),
    undo: vi.fn(),
    error: vi.fn()
}));
vi.mock('$lib/hooks', () => ({
    useAnnotationLabels: () => ({
        data: [{ annotation_label_name: 'car', annotation_label_id: 'class' }]
    }),
    useCreateAnnotation: () => ({ createAnnotation: mocks.create }),
    useDeleteAnnotation: () => ({ deleteAnnotation: mocks.remove })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ addReversibleAction: mocks.undo })
}));
vi.mock('svelte-sonner', () => ({ toast: { error: mocks.error } }));
const bounds = { x: 1, y: 2, width: 3, height: 4 };
const annotation: AnnotationView = {
    sample_id: 'original',
    parent_sample_id: 'image',
    annotation_collection_id: 'predictions',
    annotation_type: 'classification',
    annotation_label: { annotation_label_name: 'car' },
    confidence: 0.9,
    created_at: new Date()
};
const params = () => ({ collectionId: 'images', annotation, onCopied: vi.fn() });

it.each(['classification', 'object_detection', 'segmentation_mask'] as const)(
    'copies %s geometry and class without confidence, and undoes only the copy',
    async (annotation_type) => {
        const original = Object.freeze({
            ...annotation,
            annotation_type,
            object_detection_details: annotation_type === 'object_detection' ? bounds : undefined,
            segmentation_details:
                annotation_type === 'segmentation_mask'
                    ? { ...bounds, segmentation_mask: [0, 2, 3] }
                    : undefined
        });
        mocks.create.mockResolvedValue({ ...original, sample_id: 'copy' });
        const current = { ...params(), annotation: original };
        const action = useCopyAnnotationToSource(() => current);
        expect(await action.copy('human')).toBe(true);
        expect(mocks.create).toHaveBeenLastCalledWith({
            parent_sample_id: 'image',
            annotation_type,
            annotation_label_id: 'class',
            annotation_collection_name: 'human',
            ...original.object_detection_details,
            ...original.segmentation_details
        });
        current.collectionId = 'another-collection';
        await mocks.undo.mock.lastCall![0].execute();
        expect(mocks.remove).toHaveBeenLastCalledWith('copy', annotation_type, 'images');
    }
);

it('blocks repeated requests, reports failure, and allows retry', async () => {
    vi.resetAllMocks();
    mocks.create
        .mockRejectedValueOnce(new Error('offline'))
        .mockResolvedValueOnce({ ...annotation, sample_id: 'copy' });
    const action = useCopyAnnotationToSource(params);
    const request = action.copy('human');
    expect(await action.copy('human')).toBe(false);
    expect(mocks.create).toHaveBeenCalledOnce();
    expect(await request).toBe(false);
    expect(mocks.error).toHaveBeenCalled();
    expect(mocks.undo).not.toHaveBeenCalled();
    expect(await action.copy('human')).toBe(true);
});
