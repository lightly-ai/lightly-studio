import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLabelWithModel } from './useLabelWithModel.svelte';

const mocks = vi.hoisted(() => ({
    mutateAsync: vi.fn(),
    saveAnnotationPreviews: vi.fn(),
    toastError: vi.fn(),
    toastSuccess: vi.fn()
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
vi.mock('svelte-sonner', () => ({
    toast: { error: mocks.toastError, success: mocks.toastSuccess }
}));
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

    it('shows an inline error when the run fails', async () => {
        const { labelWithModel } = setup();
        mocks.mutateAsync.mockRejectedValueOnce(new Error('server down'));

        await labelWithModel.generate();

        expect(labelWithModel.generationError).toContain('Could not generate suggestions');
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
        labelWithModel.review.acceptAll();
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
        labelWithModel.review.acceptAll();
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
    it('saves corrected classes only for accepted suggestions and keeps rejected suggestions', async () => {
        const { labelWithModel } = setup();
        await generateResults(labelWithModel);
        const [first, second] = labelWithModel.review.suggestions;
        labelWithModel.review.focus(first.id);
        labelWithModel.review.changeClass('fox');
        labelWithModel.review.accept(first.id);
        labelWithModel.review.reject(second.id);
        mocks.saveAnnotationPreviews.mockImplementationOnce(
            async ({ previews, onPreviewSaved }) => {
                expect(previews).toEqual([
                    { preview: expect.objectContaining({ class_name: 'fox' }), className: 'fox' }
                ]);
                onPreviewSaved(previews[0].preview);
            }
        );

        await labelWithModel.save();

        expect(labelWithModel.predictions).toEqual([dog]);
        expect(labelWithModel.canSave).toBe(false);
        expect(mocks.toastSuccess).toHaveBeenCalledWith('Saved 1 annotation.');
        labelWithModel.review.accept(second.id);
        expect(labelWithModel.canSave).toBe(true);
    });

    it('keeps class corrections and selection after failed regeneration', async () => {
        const { labelWithModel, params } = setup();
        await generateResults(labelWithModel);
        const first = labelWithModel.review.suggestions[0];
        labelWithModel.review.focus(first.id);
        labelWithModel.review.changeClass('fox');
        labelWithModel.review.reject(first.id);
        params.threshold = 0.7;
        expect(labelWithModel.needsRegeneration).toBe(true);
        mocks.mutateAsync.mockRejectedValueOnce(new Error('offline'));

        await labelWithModel.generate();

        expect(labelWithModel.generationError).toContain('Could not generate suggestions');
        expect(labelWithModel.review.focusedSuggestion).toMatchObject({
            id: first.id,
            status: 'rejected',
            preview: { class_name: 'fox' }
        });
        expect(labelWithModel.needsRegeneration).toBe(true);
    });

    it('waits for confirmation before replacing a draft and can keep reviewing', async () => {
        const { labelWithModel } = setup();
        await generateResults(labelWithModel);
        const changeModel = vi.fn();
        labelWithModel.requestChange(changeModel);
        expect(changeModel).not.toHaveBeenCalled();
        expect(labelWithModel.pendingChange).not.toBeNull();
        labelWithModel.cancelChange();
        expect(labelWithModel.predictions).toHaveLength(2);
        expect(labelWithModel.pendingChange).toBeNull();
        labelWithModel.requestChange(changeModel);
        labelWithModel.confirmChange();
        expect(changeModel).toHaveBeenCalledOnce();
    });

    it('ignores a stale inference response after closing the tool', async () => {
        const { labelWithModel } = setup();
        const response = Promise.withResolvers<{ predictions: (typeof cat)[] }>();
        mocks.mutateAsync.mockReturnValueOnce(response.promise);
        const generation = labelWithModel.generate();
        labelWithModel.clear();
        flushSync();
        response.resolve({ predictions: [cat] });
        await generation;
        expect(labelWithModel.predictions).toEqual([]);
    });

    it('retries only the remaining selected suggestions after a partial save', async () => {
        const { labelWithModel } = setup();
        await generateResults(labelWithModel);
        labelWithModel.review.acceptAll();
        mocks.saveAnnotationPreviews.mockImplementationOnce(
            async ({ previews, onPreviewSaved }) => {
                onPreviewSaved(previews[0].preview);
                throw new Error('offline');
            }
        );
        await labelWithModel.save();
        mocks.saveAnnotationPreviews.mockImplementationOnce(
            async ({ previews, onPreviewSaved }) => {
                expect(previews).toEqual([{ preview: dog, className: 'dog' }]);
                onPreviewSaved(previews[0].preview);
            }
        );
        await labelWithModel.save();
        expect(labelWithModel.predictions).toEqual([]);
    });
    it('saves only accepted results with the edited box', async () => {
        const { labelWithModel } = setup();
        await generateResults(labelWithModel);
        expect(labelWithModel.canSave).toBe(false);
        const first = labelWithModel.review.suggestions[0];
        labelWithModel.review.updateBox(
            first.id,
            { x: 2, y: 3, width: 10, height: 15 },
            { width: 100, height: 100 }
        );
        labelWithModel.review.accept(first.id);
        mocks.saveAnnotationPreviews.mockImplementationOnce(
            async ({ previews, onPreviewSaved }) => {
                expect(previews).toEqual([
                    {
                        preview: { ...cat, bbox: { x: 2, y: 3, width: 10, height: 15 } },
                        className: 'cat'
                    }
                ]);
                onPreviewSaved(previews[0].preview);
            }
        );
        await labelWithModel.save();
        expect(labelWithModel.predictions).toEqual([dog]);
        expect(labelWithModel.review.pendingCount).toBe(1);
    });

    it('clears pending confirmations when closing the tool and does not warn for rejected suggestions', async () => {
        const { labelWithModel } = setup();
        await generateResults(labelWithModel);
        labelWithModel.requestChange(vi.fn());
        labelWithModel.clear();
        expect(labelWithModel.pendingChange).toBeNull();
        expect(labelWithModel.hasUnsavedSuggestions).toBe(false);
        await generateResults(labelWithModel);
        labelWithModel.review.rejectAll();
        const navigate = vi.fn();
        labelWithModel.requestChange(navigate);
        expect(navigate).toHaveBeenCalledOnce();
        expect(labelWithModel.hasUnsavedSuggestions).toBe(false);
    });
});
