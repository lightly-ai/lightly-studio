import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readAnnotationLabelsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useSaveAnnotationPreviews } from './useSaveAnnotationPreviews';

const mocks = vi.hoisted(() => ({
    createAnnotation: vi.fn(),
    createLabel: vi.fn(),
    invalidateQueries: vi.fn()
}));

vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));
vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'dataset-1' } } }));
vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [] })
}));
vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({ createAnnotation: mocks.createAnnotation })
}));
vi.mock('$lib/hooks/useCreateLabel/useCreateLabel', () => ({
    useCreateLabel: () => ({ createLabel: mocks.createLabel })
}));

const makePreview = (x: number) => ({
    bbox: { x, y: 0, width: 1, height: 1 },
    segmentation_mask: [x, 1],
    score: null,
    class_name: null
});
const first = makePreview(1);
const second = makePreview(2);

const save = (onPreviewSaved: (preview: unknown) => void) =>
    useSaveAnnotationPreviews({ getCollectionId: () => 'collection-1' }).saveAnnotationPreviews({
        sampleId: 'sample-1',
        saveAs: 'mask',
        annotationSource: 'source',
        previews: [
            { preview: first, className: 'cat' },
            { preview: second, className: 'cat' }
        ],
        onPreviewSaved
    });

describe('useSaveAnnotationPreviews', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.createLabel.mockResolvedValue({ annotation_label_id: 'label-1' });
    });

    it('creates a new class once and refreshes the labels once', async () => {
        const onPreviewSaved = vi.fn();
        mocks.createAnnotation.mockResolvedValue({});

        await save(onPreviewSaved);

        expect(mocks.createLabel).toHaveBeenCalledTimes(1);
        expect(mocks.createAnnotation).toHaveBeenCalledTimes(2);
        expect(mocks.invalidateQueries).toHaveBeenCalledTimes(1);
        expect(mocks.invalidateQueries).toHaveBeenCalledWith({
            queryKey: readAnnotationLabelsQueryKey({ path: { collection_id: 'collection-1' } })
        });
        expect(onPreviewSaved.mock.calls).toEqual([[first], [second]]);
    });

    it('reports only the saved previews and rejects when a create fails', async () => {
        const onPreviewSaved = vi.fn();
        const error = new Error('create failed');
        mocks.createAnnotation.mockResolvedValueOnce({}).mockRejectedValueOnce(error);

        await expect(save(onPreviewSaved)).rejects.toBe(error);

        expect(onPreviewSaved.mock.calls).toEqual([[first]]);
    });

    it('reuses a class created by a failed call on retry while the label list is stale', async () => {
        const hook = useSaveAnnotationPreviews({ getCollectionId: () => 'collection-1' });
        const params = {
            sampleId: 'sample-1',
            saveAs: 'mask' as const,
            annotationSource: 'source',
            onPreviewSaved: vi.fn()
        };
        mocks.createAnnotation
            .mockResolvedValueOnce({})
            .mockRejectedValueOnce(new Error('create failed'))
            .mockResolvedValueOnce({});

        await expect(
            hook.saveAnnotationPreviews({
                ...params,
                previews: [
                    { preview: first, className: 'cat' },
                    { preview: second, className: 'cat' }
                ]
            })
        ).rejects.toThrow('create failed');
        await hook.saveAnnotationPreviews({
            ...params,
            previews: [{ preview: second, className: 'cat' }]
        });

        expect(mocks.createLabel).toHaveBeenCalledTimes(1);
        expect(mocks.createAnnotation).toHaveBeenLastCalledWith(
            expect.objectContaining({ annotation_label_id: 'label-1' })
        );
    });
});
