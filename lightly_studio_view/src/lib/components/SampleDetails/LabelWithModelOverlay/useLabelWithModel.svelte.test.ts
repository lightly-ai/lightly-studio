import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLabelWithModel } from './useLabelWithModel.svelte';

const mocks = vi.hoisted(() => ({
    mutateAsync: vi.fn(),
    saveAnnotationPreviews: vi.fn(),
    toastError: vi.fn()
}));

vi.mock('@tanstack/svelte-query', () => ({
    createMutation: () => ({ mutateAsync: mocks.mutateAsync })
}));
vi.mock('$lib/hooks', () => ({
    useSaveAnnotationPreviews: () => ({ saveAnnotationPreviews: mocks.saveAnnotationPreviews })
}));
vi.mock('svelte-sonner', () => ({ toast: { error: mocks.toastError } }));
vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'dataset-1' } } }));

const cat = {
    class_name: 'cat',
    bbox: { x: 1, y: 0, width: 2, height: 2 },
    segmentation_mask: null,
    score: 0.9
};
const dog = { ...cat, class_name: 'dog', bbox: { x: 5, y: 0, width: 2, height: 2 }, score: 0.6 };

let cleanup = () => {};

const setup = () => {
    const params = $state<{ sampleId: string; modelId: string | null }>({
        sampleId: 'sample-1',
        modelId: 'ltdetrv2-s-coco'
    });
    const onSaved = vi.fn();
    let labelWithModel!: ReturnType<typeof useLabelWithModel>;
    cleanup = $effect.root(() => {
        labelWithModel = useLabelWithModel(() => ({
            collectionId: 'collection-1',
            sampleId: params.sampleId,
            modelId: params.modelId,
            threshold: 0.4,
            saveAs: 'box',
            annotationSource: 'source',
            onSaved
        }));
    });
    flushSync();
    return { labelWithModel, params, onSaved };
};

const generateResults = async (labelWithModel: ReturnType<typeof useLabelWithModel>) => {
    mocks.mutateAsync.mockResolvedValueOnce({ predictions: [cat, dog] });
    await labelWithModel.generate();
    expect(labelWithModel.predictions).toHaveLength(2);
};

describe('useLabelWithModel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => cleanup());

    it('runs the selected model on the sample', async () => {
        const { labelWithModel } = setup();

        await generateResults(labelWithModel);

        expect(mocks.mutateAsync).toHaveBeenCalledWith({
            body: {
                collection_id: 'collection-1',
                sample_id: 'sample-1',
                model_id: 'ltdetrv2-s-coco',
                threshold: 0.4
            }
        });
        expect(labelWithModel.isGenerating).toBe(false);
    });

    it('does not run without a model', async () => {
        const { labelWithModel, params } = setup();
        params.modelId = null;
        flushSync();

        expect(labelWithModel.canGenerate).toBe(false);
        await labelWithModel.generate();

        expect(mocks.mutateAsync).not.toHaveBeenCalled();
    });

    it('reports an empty result', async () => {
        const { labelWithModel } = setup();
        mocks.mutateAsync.mockResolvedValueOnce({ predictions: [] });

        await labelWithModel.generate();

        expect(labelWithModel.isEmptyResult).toBe(true);
    });

    it('shows a toast when the run fails', async () => {
        const { labelWithModel } = setup();
        mocks.mutateAsync.mockRejectedValueOnce(new Error('server down'));

        await labelWithModel.generate();

        expect(mocks.toastError).toHaveBeenCalledOnce();
        expect(labelWithModel.predictions).toEqual([]);
    });

    it('drops the results when the sample or the model changes', async () => {
        const { labelWithModel, params } = setup();
        await generateResults(labelWithModel);

        params.sampleId = 'sample-2';
        flushSync();
        expect(labelWithModel.predictions).toEqual([]);

        await generateResults(labelWithModel);
        params.modelId = 'ltdetrv2-seg-s-coco';
        flushSync();
        expect(labelWithModel.predictions).toEqual([]);
    });

    it('removes a deleted prediction', async () => {
        const { labelWithModel } = setup();
        await generateResults(labelWithModel);

        labelWithModel.removePrediction(labelWithModel.predictions[0]);

        expect(labelWithModel.predictions).toEqual([dog]);
    });

    it('saves each prediction with its own class', async () => {
        const { labelWithModel, onSaved } = setup();
        await generateResults(labelWithModel);
        mocks.saveAnnotationPreviews.mockImplementationOnce(
            async ({ previews, onPreviewSaved }) => {
                for (const { preview } of previews) onPreviewSaved(preview);
            }
        );

        await labelWithModel.save();

        expect(mocks.saveAnnotationPreviews).toHaveBeenCalledWith(
            expect.objectContaining({
                sampleId: 'sample-1',
                saveAs: 'box',
                annotationSource: 'source',
                previews: [
                    { preview: cat, className: 'cat' },
                    { preview: dog, className: 'dog' }
                ]
            })
        );
        expect(labelWithModel.predictions).toEqual([]);
        expect(onSaved).toHaveBeenCalledOnce();
    });

    it('keeps the unsaved predictions when the save fails', async () => {
        const { labelWithModel, onSaved } = setup();
        await generateResults(labelWithModel);
        mocks.saveAnnotationPreviews.mockImplementationOnce(
            async ({ previews, onPreviewSaved }) => {
                onPreviewSaved(previews[0].preview);
                throw new Error('failed');
            }
        );

        await labelWithModel.save();

        expect(labelWithModel.predictions).toEqual([dog]);
        expect(mocks.toastError).toHaveBeenCalledOnce();
        expect(onSaved).not.toHaveBeenCalled();
    });
});
