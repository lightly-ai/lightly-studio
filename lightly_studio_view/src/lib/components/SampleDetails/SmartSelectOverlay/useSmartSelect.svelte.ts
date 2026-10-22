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
    // Drops responses that a newer request or a clear made stale.
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

    const clear = () => {
        sequence += 1;
        points = [];
        preview = null;
        hintedClass = null;
    };

    // Drops a request from a previous sample, e.g. after the overlay was keyed by a new one.
    $effect(() => clear);

    const addPoint = (point: SmartSelectPoint, className: string | null) => {
        if (isSaving) return;
        points = [...points, point];
        hintedClass = className ?? hintedClass;
        if (canInferFromPoints(points)) void infer({ points });
    };

    const selectBox = (box: NormalizedBox) => {
        if (isSaving) return;
        clear();
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
                onPreviewSaved: clear
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
        addPoint,
        selectBox,
        clear,
        save
    };
};
