import { toast } from 'svelte-sonner';
import { createMutation } from '@tanstack/svelte-query';
import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import { createInteractiveAnnotationPreviewMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useSaveAnnotationPreviews } from '$lib/hooks';
import {
    getAnnotationPreviewErrorMessage,
    pickClassName
} from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
import type { boxFromPoints } from '$lib/components/SampleDetails/useDragBox/useDragBox.helpers';
import { page } from '$app/state';
import { canInferFromPoints, type SmartSelectPoint } from './SmartSelectOverlay.helpers';

type NormalizedBox = ReturnType<typeof boxFromPoints>;
type SaveAs = Parameters<
    ReturnType<typeof useSaveAnnotationPreviews>['saveAnnotationPreviews']
>[0]['saveAs'];
// One box, because the endpoint previews a single object
type SmartSelectPrompt = { points: SmartSelectPoint[] } | { boxes: [NormalizedBox] };

interface UseSmartSelectParams {
    collectionId: string;
    sampleId: string;
    saveAs: SaveAs;
    annotationClass: string | null | undefined;
    annotationSource: string | null | undefined;
    onSaved: () => void;
}

// Collects point and box prompts, requests a preview for them and saves the preview.
export const useSmartSelect = (getParams: () => UseSmartSelectParams) => {
    let points = $state<SmartSelectPoint[]>([]);
    let preview = $state<AnnotationPreview | null>(null);
    let isSaving = $state(false);
    let hintedClass: string | null = null;
    // Drops responses that a newer prompt or a clear made stale.
    let sequence = 0;

    const mutation = createMutation(() => createInteractiveAnnotationPreviewMutation());
    const { saveAnnotationPreviews } = useSaveAnnotationPreviews({
        getCollectionId: () => getParams().collectionId,
        getDatasetId: () => page.params.dataset_id!
    });

    const infer = async (prompt: SmartSelectPrompt) => {
        const requestSequence = ++sequence;
        const { collectionId, sampleId } = getParams();
        try {
            const result = await mutation.mutateAsync({
                body: { collection_id: collectionId, sample_id: sampleId, ...prompt }
            });
            if (requestSequence === sequence) preview = result.prediction;
        } catch (error) {
            if (requestSequence !== sequence) return;
            toast.error(`Smart select failed: ${getAnnotationPreviewErrorMessage(error)}`);
        }
    };

    const dropPreview = () => {
        sequence += 1;
        preview = null;
    };

    const reset = () => {
        dropPreview();
        points = [];
        hintedClass = null;
    };

    // Drops a request from a previous sample, e.g. after the overlay was keyed by a new one.
    $effect(() => reset);

    // Keeps the preview while a save runs, so a failed save can be retried.
    const clear = () => {
        if (!isSaving) reset();
    };

    const addPoint = (point: SmartSelectPoint, className: string | null) => {
        if (isSaving) return;
        // The endpoint takes points or a box, so a click drops a box preview.
        if (points.length === 0) clear();
        points = [...points, point];
        // The preview no longer matches the points, even if no new request starts.
        dropPreview();
        hintedClass = className ?? hintedClass;
        if (canInferFromPoints(points)) void infer({ points });
    };

    const selectBox = (box: NormalizedBox) => {
        if (isSaving) return;
        reset();
        void infer({ boxes: [box] });
    };

    const save = async () => {
        if (!preview || isSaving) return;
        isSaving = true;
        const { sampleId, saveAs, annotationClass, annotationSource, onSaved } = getParams();
        const className = pickClassName({ selected: annotationClass, hint: hintedClass });
        try {
            await saveAnnotationPreviews({
                sampleId,
                saveAs,
                annotationSource,
                previews: [{ preview, className }],
                onPreviewSaved: reset
            });
            onSaved();
        } catch (error) {
            toast.error(
                `Could not save the annotation: ${getAnnotationPreviewErrorMessage(error)}`
            );
        } finally {
            isSaving = false;
        }
    };

    return {
        get points() {
            return points;
        },
        get preview() {
            return preview;
        },
        get canSave() {
            return preview !== null && !isSaving;
        },
        get isPending() {
            return mutation.isPending;
        },
        get needsPositivePoint() {
            return points.length > 0 && !canInferFromPoints(points);
        },
        addPoint,
        selectBox,
        clear,
        save
    };
};
