import { toast } from 'svelte-sonner';
import { createMutation } from '@tanstack/svelte-query';
import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';
import { createModelAnnotationPreviewMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useSaveAnnotationPreviews } from '$lib/hooks';
import { getAnnotationPreviewErrorMessage } from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
import { page } from '$app/state';

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
    onSaved: () => void;
}

// Runs a model on the sample, keeps its previews until the user saves or deletes them.
export const useLabelWithModel = (getParams: () => UseLabelWithModelParams) => {
    let predictions = $state<ModelAnnotationPreview[]>([]);
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
        if (isSaveIgnored || !isSaving) predictions = [];
    };

    const canSave = () => predictions.length > 0 && !isSaving && !isGenerating;
    const canGenerate = () => !isSaving && !isGenerating && !!getParams().modelId;

    const clear = () => dropPredictions();

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
            predictions = result.predictions;
            isEmptyResult = predictions.length === 0;
        } catch (error) {
            if (requestSequence !== sequence) return;
            toast.error(`Could not label the image: ${getAnnotationPreviewErrorMessage(error)}`);
        } finally {
            if (requestSequence === sequence) isGenerating = false;
        }
    };

    const filterOutPrediction = (preview: ModelAnnotationPreview) => {
        predictions = predictions.filter((prediction) => prediction !== preview);
    };

    const removePrediction = (preview: ModelAnnotationPreview) => {
        if (!isSaving) filterOutPrediction(preview);
    };

    const save = async () => {
        const { sampleId, saveAs, annotationSource, onSaved } = getParams();
        if (!canSave()) return;
        isSaving = true;
        try {
            await saveAnnotationPreviews({
                sampleId,
                saveAs,
                annotationSource,
                previews: predictions.map((preview) => ({
                    preview,
                    className: preview.class_name
                })),
                onPreviewSaved: filterOutPrediction
            });
            if (!isDisposed) onSaved();
        } catch (error) {
            toast.error(
                `Could not save the annotations: ${getAnnotationPreviewErrorMessage(error)}`
            );
        } finally {
            isSaving = false;
            if (isDropPending) dropPredictions();
        }
    };

    return {
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
        removePrediction,
        clear,
        save
    };
};
