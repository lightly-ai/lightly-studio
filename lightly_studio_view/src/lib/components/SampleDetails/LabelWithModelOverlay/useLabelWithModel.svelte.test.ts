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
vi.mock('$lib/hooks', async () => ({
    isAnnotationSourceBlocked: (
        await import('$lib/hooks/useAnnotationTarget/annotationSourceGuard')
    ).isAnnotationSourceBlocked,
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

const setup = (blockedReason: string | null = null) => {
    const params = $state<{ sampleId: string; modelId: string | null; threshold: number }>({
        sampleId: 'sample-1',
        modelId: 'ltdetrv2-s-coco',
        threshold: 0.4
    });
    const onSaved = vi.fn();
    let labelWithModel!: ReturnType<typeof useLabelWithModel>;
    cleanup = $effect.root(() => {
        labelWithModel = useLabelWithModel(() => ({
            collectionId: 'collection-1',
            sampleId: params.sampleId,
            modelId: params.modelId,
            threshold: params.threshold,
            saveAs: 'box',
            annotationSource: 'source',
            annotationSourceBlockedReason: blockedReason,
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

    it('drops the results when the sample, the model or the threshold changes', async () => {
        const { labelWithModel, params } = setup();
        await generateResults(labelWithModel);

        params.sampleId = 'sample-2';
        flushSync();
        expect(labelWithModel.predictions).toEqual([]);

        await generateResults(labelWithModel);
        params.modelId = 'ltdetrv2-seg-s-coco';
        flushSync();
        expect(labelWithModel.predictions).toEqual([]);

        await generateResults(labelWithModel);
        params.threshold = 0.8;
        flushSync();
        expect(labelWithModel.predictions).toEqual([]);
    });

    it('keeps the predictions until the save ends when the model changes', async () => {
        const { labelWithModel, params } = setup();
        await generateResults(labelWithModel);
        let endSave = () => {};
        mocks.saveAnnotationPreviews.mockImplementationOnce(
            () => new Promise<void>((resolve) => (endSave = resolve))
        );

        const save = labelWithModel.save();
        params.modelId = 'ltdetrv2-seg-s-coco';
        flushSync();
        expect(labelWithModel.predictions).toHaveLength(2);

        endSave();
        await save;
        expect(labelWithModel.predictions).toEqual([]);
    });

    it('removes a deleted prediction', async () => {
        const { labelWithModel } = setup();
        await generateResults(labelWithModel);

        labelWithModel.removePrediction(labelWithModel.predictions[0]);

        expect(labelWithModel.predictions).toEqual([dog]);
    });

    it('keeps the predictions and tells why when the annotation source is blocked', async () => {
        const { labelWithModel, onSaved } = setup('Pick where new annotations go.');
        await generateResults(labelWithModel);

        await labelWithModel.save();

        expect(mocks.saveAnnotationPreviews).not.toHaveBeenCalled();
        expect(mocks.toastError).toHaveBeenCalledWith('Pick where new annotations go.');
        expect(labelWithModel.predictions).toHaveLength(2);
        expect(onSaved).not.toHaveBeenCalled();
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
