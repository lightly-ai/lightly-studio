import { toast } from 'svelte-sonner';
import { createMutation } from '@tanstack/svelte-query';
import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';
import { createModelAnnotationPreviewMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { isAnnotationSourceBlocked, useSaveAnnotationPreviews } from '$lib/hooks';
import { getAnnotationPreviewErrorMessage } from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
import { page } from '$app/state';
import { useModelSuggestionReview } from './useModelSuggestionReview.svelte';

type SaveAs = Parameters<
    ReturnType<typeof useSaveAnnotationPreviews>['saveAnnotationPreviews']
>[0]['saveAs'];

interface UseLabelWithModelParams {
    collectionId: string;
    sampleId: string;
    modelId: string | null;
    threshold: number;
    saveAs: SaveAs;
    annotationSource: string | null | undefined;
    annotationSourceBlockedReason?: string | null;
    onSaved: () => void;
}

interface UseLabelWithModelReturn {
    review: ReturnType<typeof useModelSuggestionReview>;
    readonly generationError: string | null;
    readonly needsRegeneration: boolean;
    readonly annotationSource: string;
    readonly annotationSourceBlockedReason: string | null;
    readonly pendingChange: (() => void) | null;
    requestChange: (action: () => void) => void;
    confirmChange: () => void;
    cancelChange: () => void;
    readonly predictions: ModelAnnotationPreview[];
    readonly isGenerating: boolean;
    readonly isEmptyResult: boolean;
    readonly isSaving: boolean;
    readonly canSave: boolean;
    readonly canGenerate: boolean;
    generate: () => Promise<void>;
    clear: () => void;
    save: () => Promise<void>;
}

// Runs a model on the sample, keeps its previews until the user saves or deletes them.
export const useLabelWithModel = (
    getParams: () => UseLabelWithModelParams
): UseLabelWithModelReturn => {
    const review = useModelSuggestionReview();
    const predictions = $derived(review.suggestions.map((suggestion) => suggestion.preview));
    let generationError = $state<string | null>(null);
    let generatedThreshold = $state<number | null>(null);
    let pendingChange = $state<(() => void) | null>(null);
    let isGenerating = $state(false);
    // Set when the last run returned no objects.
    let isEmptyResult = $state(false);
    let isSaving = $state(false);
    // A clear during a save drops the unsaved predictions once it ends.
    let isDropPending = false;
    // Drops responses that a newer run or clear made stale.
    let sequence = 0;
    let isDisposed = false;

    const mutation = createMutation(() => createModelAnnotationPreviewMutation());
    const { saveAnnotationPreviews } = useSaveAnnotationPreviews({
        getCollectionId: () => getParams().collectionId,
        getDatasetId: () => page.params.dataset_id!
    });

    const cancelRun = () => {
        sequence += 1;
        isGenerating = false;
        isEmptyResult = false;
    };

    // With isSaveIgnored, drops the predictions right away, also while a save runs.
    const dropPredictions = ({ isSaveIgnored = false } = {}) => {
        cancelRun();
        isDropPending = isSaving && !isSaveIgnored;
        if (isSaveIgnored || !isSaving) review.replace([]);
        generationError = null;
        generatedThreshold = null;
    };

    const canSave = () =>
        review.includedSuggestions.length > 0 &&
        !isSaving &&
        !isGenerating &&
        !getParams().annotationSourceBlockedReason;
    const canGenerate = () => !isSaving && !isGenerating && !!getParams().modelId;

    const clear = () => dropPredictions();

    const requestChange = (action: () => void) => {
        if (isSaving || isGenerating) return;
        if (predictions.length > 0) pendingChange = action;
        else action();
    };

    const confirmChange = () => {
        const action = pendingChange;
        pendingChange = null;
        action?.();
    };

    const currentSampleId = $derived(getParams().sampleId);
    const currentModelId = $derived(getParams().modelId);

    // Drops the results of a previous sample or model, also while a save runs.
    $effect(() => {
        void currentSampleId;
        void currentModelId;
        return () => dropPredictions({ isSaveIgnored: true });
    });

    $effect(() => () => {
        isDisposed = true;
    });

    const generate = async () => {
        const { collectionId, sampleId, modelId, threshold } = getParams();
        if (!modelId || !canGenerate()) return;
        const requestSequence = ++sequence;
        isGenerating = true;
        isEmptyResult = false;
        generationError = null;
        try {
            const result = await mutation.mutateAsync({
                body: {
                    collection_id: collectionId,
                    sample_id: sampleId,
                    model_id: modelId,
                    threshold
                }
            });
            if (requestSequence !== sequence) return;
            review.replace(result.predictions);
            generatedThreshold = threshold;
            isEmptyResult = predictions.length === 0;
        } catch (error) {
            if (requestSequence !== sequence) return;
            generationError = `Could not generate suggestions: ${getAnnotationPreviewErrorMessage(error)}`;
        } finally {
            if (requestSequence === sequence) isGenerating = false;
        }
    };

    const filterOutPrediction = (preview: ModelAnnotationPreview) => {
        review.remove(preview);
    };

    const save = async () => {
        const { sampleId, saveAs, annotationSource, annotationSourceBlockedReason, onSaved } =
            getParams();
        if (isAnnotationSourceBlocked({ annotationSourceBlockedReason })) return;
        if (!canSave()) return;
        const selectedPreviews = review.includedSuggestions.map((suggestion) => suggestion.preview);
        isSaving = true;
        let savedCount = 0;
        try {
            await saveAnnotationPreviews({
                sampleId,
                saveAs,
                annotationSource,
                previews: selectedPreviews.map((preview) => ({
                    preview,
                    className: preview.class_name
                })),
                onPreviewSaved: (preview) => {
                    filterOutPrediction(preview);
                    savedCount += 1;
                }
            });
            if (!isDisposed) onSaved();
        } catch (error) {
            toast.error(
                `Could not save the annotations: ${getAnnotationPreviewErrorMessage(error)}`
            );
        } finally {
            if (savedCount > 0 && !isDisposed)
                toast.success(
                    `Saved ${savedCount} ${savedCount === 1 ? 'annotation' : 'annotations'}.`
                );
            isSaving = false;
            if (isDropPending) dropPredictions();
        }
    };

    return {
        review,
        get generationError() {
            return generationError;
        },
        get needsRegeneration() {
            return predictions.length > 0 && generatedThreshold !== getParams().threshold;
        },
        get annotationSource() {
            return getParams().annotationSource || 'Default annotation source';
        },
        get annotationSourceBlockedReason() {
            return getParams().annotationSourceBlockedReason ?? null;
        },
        get pendingChange() {
            return pendingChange;
        },
        requestChange,
        confirmChange,
        cancelChange: () => {
            pendingChange = null;
        },
        get predictions() {
            return predictions;
        },
        get isGenerating() {
            return isGenerating;
        },
        get isEmptyResult() {
            return isEmptyResult;
        },
        get isSaving() {
            return isSaving;
        },
        get canSave() {
            return canSave();
        },
        get canGenerate() {
            return canGenerate();
        },
        generate,
        clear,
        save
    };
};
