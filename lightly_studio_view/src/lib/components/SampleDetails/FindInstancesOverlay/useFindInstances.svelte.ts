import { untrack } from 'svelte';
import { toast } from 'svelte-sonner';
import { createMutation } from '@tanstack/svelte-query';
import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import { createInstancesAnnotationPreviewMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useSaveAnnotationPreviews } from '$lib/hooks';
import {
    getAnnotationPreviewErrorMessage,
    pickClassName
} from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
import type { boxFromPoints } from '$lib/components/SampleDetails/useDragBox/useDragBox.helpers';
import { page } from '$app/state';
import { buildInstancesRequestBody, canGenerateInstances } from './FindInstancesOverlay.helpers';

type NormalizedBox = ReturnType<typeof boxFromPoints>;
type SaveAs = Parameters<
    ReturnType<typeof useSaveAnnotationPreviews>['saveAnnotationPreviews']
>[0]['saveAs'];

interface UseFindInstancesParams {
    collectionId: string;
    sampleId: string;
    prompt: string;
    maxInstances: number;
    saveAs: SaveAs;
    annotationClass: string | null | undefined;
    annotationSource: string | null | undefined;
    onSaved: () => void;
}

// Collects a text prompt and boxes, requests previews of all matching instances and saves them.
export const useFindInstances = (getParams: () => UseFindInstancesParams) => {
    let boxes = $state<NormalizedBox[]>([]);
    let predictions = $state<AnnotationPreview[]>([]);
    let isGenerating = $state(false);
    let isSaving = $state(false);
    // A clear or new prompt during a save drops the unsaved predictions once it ends.
    let isDropPending = false;
    // Drops responses that a newer prompt, box or clear made stale.
    let sequence = 0;
    let isDisposed = false;
    let previousPrompt = untrack(() => getParams().prompt.trim());

    const mutation = createMutation(() => createInstancesAnnotationPreviewMutation());
    const { saveAnnotationPreviews } = useSaveAnnotationPreviews({
        getCollectionId: () => getParams().collectionId,
        getDatasetId: () => page.params.dataset_id!
    });

    const dropPredictions = () => {
        sequence += 1;
        isGenerating = false;
        isDropPending = isSaving;
        if (!isSaving) predictions = [];
    };

    const canSave = () => predictions.length > 0 && !isSaving && !isGenerating;

    const clear = () => {
        dropPredictions();
        boxes = [];
    };

    const currentSampleId = $derived(getParams().sampleId);

    // Drops the boxes, requests and results of a previous sample, also while a save runs.
    $effect(() => {
        void currentSampleId;
        return () => {
            sequence += 1;
            isGenerating = false;
            predictions = [];
            boxes = [];
        };
    });

    $effect(() => () => {
        isDisposed = true;
    });

    // A new prompt starts a new search and keeps the drawn boxes.
    $effect(() => {
        const prompt = getParams().prompt.trim();
        if (prompt === previousPrompt) return;
        previousPrompt = prompt;
        untrack(dropPredictions);
    });

    const generate = async () => {
        const { collectionId, sampleId, prompt, maxInstances } = getParams();
        if (isSaving || isGenerating || !canGenerateInstances({ prompt })) return;
        const requestSequence = ++sequence;
        isGenerating = true;
        try {
            const result = await mutation.mutateAsync({
                body: buildInstancesRequestBody({
                    collectionId,
                    sampleId,
                    prompt,
                    boxes: $state.snapshot(boxes),
                    maxInstances
                })
            });
            if (requestSequence !== sequence) return;
            predictions = result.predictions;
            if (predictions.length > 0) boxes = [];
        } catch (error) {
            if (requestSequence !== sequence) return;
            toast.error(`Find all instances failed: ${getAnnotationPreviewErrorMessage(error)}`);
        } finally {
            if (requestSequence === sequence) isGenerating = false;
        }
    };

    const addBox = (box: NormalizedBox) => {
        if (isSaving) return;
        dropPredictions();
        boxes = [...boxes, box];
    };

    const removeSavedPrediction = (preview: AnnotationPreview) => {
        predictions = predictions.filter((prediction) => prediction !== preview);
    };

    const removePrediction = (preview: AnnotationPreview) => {
        if (!isSaving) removeSavedPrediction(preview);
    };

    const save = async () => {
        if (!canSave()) return;
        isSaving = true;
        const { sampleId, prompt, saveAs, annotationClass, annotationSource, onSaved } =
            getParams();
        const className = pickClassName({ selected: annotationClass, hint: prompt });
        try {
            await saveAnnotationPreviews({
                sampleId,
                saveAs,
                annotationSource,
                previews: predictions.map((preview) => ({
                    preview,
                    className
                })),
                onPreviewSaved: removeSavedPrediction
            });
            if (!isDisposed) onSaved();
        } catch (error) {
            if (isDisposed) return;
            toast.error(
                `Could not save the annotations: ${getAnnotationPreviewErrorMessage(error)}`
            );
        } finally {
            isSaving = false;
            if (isDropPending) dropPredictions();
        }
    };

    return {
        get boxes() {
            return boxes;
        },
        get predictions() {
            return predictions;
        },
        get isGenerating() {
            return isGenerating;
        },
        get canSave() {
            return canSave();
        },
        generate,
        addBox,
        removePrediction,
        clear,
        save
    };
};
