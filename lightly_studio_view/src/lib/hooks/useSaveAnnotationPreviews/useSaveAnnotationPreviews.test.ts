import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readAnnotationLabelsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useSaveAnnotationPreviews } from './useSaveAnnotationPreviews';

const mocks = vi.hoisted(() => ({
    createAnnotation: vi.fn(),
    createLabel: vi.fn(),
    fetchQuery: vi.fn(),
    invalidateQueries: vi.fn(),
    refetch: vi.fn()
}));

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    useQueryClient: () => ({
        fetchQuery: mocks.fetchQuery,
        invalidateQueries: mocks.invalidateQueries
    })
}));
vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'dataset-1' } } }));
vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({
        createAnnotation: mocks.createAnnotation,
        refetch: mocks.refetch
    })
}));
vi.mock('$lib/hooks/useCreateLabel/useCreateLabel', () => ({
    useCreateLabel: () => ({ createLabel: mocks.createLabel })
}));

const makePreview = (x: number) => ({
    bbox: { x, y: 0, width: 1, height: 1 },
    segmentation_mask: [x, 1],
    score: null
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
        mocks.fetchQuery.mockResolvedValue([]);
    });

    it('creates a new class once and refreshes the labels and annotations once', async () => {
        const onPreviewSaved = vi.fn();
        mocks.createAnnotation.mockResolvedValue({});

        await save(onPreviewSaved);

        expect(mocks.createLabel).toHaveBeenCalledTimes(1);
        expect(mocks.createAnnotation).toHaveBeenCalledTimes(2);
        expect(mocks.invalidateQueries).toHaveBeenCalledTimes(1);
        expect(mocks.invalidateQueries).toHaveBeenCalledWith({
            queryKey: readAnnotationLabelsQueryKey({ path: { collection_id: 'collection-1' } })
        });
        expect(mocks.refetch).toHaveBeenCalledTimes(1);
        expect(onPreviewSaved.mock.calls).toEqual([[first], [second]]);
    });

    it('uses an existing class without creating it', async () => {
        mocks.fetchQuery.mockResolvedValue([
            { annotation_label_name: 'cat', annotation_label_id: 'label-cat' }
        ]);
        mocks.createAnnotation.mockResolvedValue({});

        await save(vi.fn());

        expect(mocks.createLabel).not.toHaveBeenCalled();
        expect(mocks.invalidateQueries).not.toHaveBeenCalled();
        expect(mocks.createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({ annotation_label_id: 'label-cat' }),
            { skipRefetch: true }
        );
    });

    it('reports only the saved previews and rejects when a create fails', async () => {
        const onPreviewSaved = vi.fn();
        const error = new Error('create failed');
        mocks.createAnnotation.mockResolvedValueOnce({}).mockRejectedValueOnce(error);

        await expect(save(onPreviewSaved)).rejects.toBe(error);

        expect(onPreviewSaved.mock.calls).toEqual([[first]]);
        expect(mocks.refetch).toHaveBeenCalledTimes(1);
    });

    it('reuses a class created by a failed call on retry', async () => {
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
        mocks.fetchQuery.mockResolvedValue([
            { annotation_label_name: 'cat', annotation_label_id: 'label-1' }
        ]);
        await hook.saveAnnotationPreviews({
            ...params,
            previews: [{ preview: second, className: 'cat' }]
        });

        expect(mocks.createLabel).toHaveBeenCalledTimes(1);
        expect(mocks.createAnnotation).toHaveBeenLastCalledWith(
            expect.objectContaining({ annotation_label_id: 'label-1' }),
            { skipRefetch: true }
        );
    });
});
