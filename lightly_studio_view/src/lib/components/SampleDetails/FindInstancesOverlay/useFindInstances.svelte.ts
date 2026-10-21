import { untrack } from 'svelte';
import { toast } from 'svelte-sonner';
import { createMutation } from '@tanstack/svelte-query';
import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import { createInstancesAnnotationPreviewMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useSaveAnnotationPreviews } from '$lib/hooks/useSaveAnnotationPreviews';
import {
    getAnnotationPreviewErrorMessage,
    resolveAnnotationClassName,
    type NormalizedBox,
    type SaveAs
} from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
import { buildInstancesRequestBody, canGenerateInstances } from './FindInstancesOverlay.helpers';

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
    // Prompt of the current predictions, fixed when they were generated so retries keep it.
    let resultsPrompt = '';
    let isGenerating = $state(false);
    let isSaving = $state(false);
    // Drops responses that a newer prompt, box or clear made stale.
    let sequence = 0;
    let previousPrompt = untrack(() => getParams().prompt);

    const mutation = createMutation(() => createInstancesAnnotationPreviewMutation());
    const { saveAnnotationPreviews } = useSaveAnnotationPreviews({
        getCollectionId: () => getParams().collectionId
    });

    // Keeps the predictions while a save runs, so a failed save keeps the unsaved ones.
    const dropPredictions = () => {
        sequence += 1;
        isGenerating = false;
        if (isSaving) return;
        predictions = [];
        resultsPrompt = '';
    };

    const canSave = () => predictions.length > 0 && !isSaving && !isGenerating;

    const clear = () => {
        dropPredictions();
        boxes = [];
    };

    // Drops a request from a previous sample, e.g. after the overlay was keyed by a new one.
    $effect(() => clear);

    // A new prompt starts a new search and keeps the drawn boxes.
    $effect(() => {
        const { prompt } = getParams();
        if (prompt === previousPrompt) return;
        previousPrompt = prompt;
        untrack(dropPredictions);
    });

    const generate = async () => {
        const { collectionId, sampleId, prompt, maxInstances } = getParams();
        if (isSaving || !canGenerateInstances({ prompt })) return;
        const requestSequence = ++sequence;
        isGenerating = true;
        try {
            const result = await mutation.mutateAsync({
                body: buildInstancesRequestBody({
                    collectionId,
                    sampleId,
                    prompt,
                    boxes,
                    maxInstances
                })
            });
            if (requestSequence !== sequence) return;
            predictions = result.predictions;
            resultsPrompt = prompt;
            boxes = [];
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

    const removePrediction = (preview: AnnotationPreview) => {
        if (isSaving) return;
        predictions = predictions.filter((prediction) => prediction !== preview);
    };

    const removeSavedPrediction = (preview: AnnotationPreview) => {
        predictions = predictions.filter((prediction) => prediction !== preview);
    };

    const save = async () => {
        if (!canSave()) return;
        isSaving = true;
        const { sampleId, saveAs, annotationClass, annotationSource, onSaved } = getParams();
        const className = resolveAnnotationClassName([annotationClass, resultsPrompt]);
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
            onSaved();
        } catch (error) {
            toast.error(
                `Could not save the annotations: ${getAnnotationPreviewErrorMessage(error)}`
            );
        } finally {
            isSaving = false;
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
