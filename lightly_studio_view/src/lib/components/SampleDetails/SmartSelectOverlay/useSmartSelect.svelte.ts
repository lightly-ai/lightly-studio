import { toast } from 'svelte-sonner';
import { createMutation } from '@tanstack/svelte-query';
import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import { createInteractiveAnnotationPreviewMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useSaveAnnotationPreviews } from '$lib/hooks';
import { useReversibleActions } from '$lib/hooks/useReversibleActions';
import { getAnnotationPreviewErrorMessage } from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
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
    let box = $state<NormalizedBox | null>(null);
    let isPending = $state(false);
    const undoGroup = crypto.randomUUID();
    const { addReversibleAction, clearReversibleActionsByGroupId } = useReversibleActions();
    // Drops responses that a newer prompt or a clear made stale.
    let sequence = 0;

    const mutation = createMutation(() => createInteractiveAnnotationPreviewMutation());
    const { saveAnnotationPreviews } = useSaveAnnotationPreviews({
        getCollectionId: () => getParams().collectionId,
        getDatasetId: () => page.params.dataset_id!
    });

    const infer = async (prompt: SmartSelectPrompt) => {
        const requestSequence = ++sequence;
        isPending = true;
        const { collectionId, sampleId } = getParams();
        try {
            const result = await mutation.mutateAsync({
                body: { collection_id: collectionId, sample_id: sampleId, ...prompt }
            });
            if (requestSequence === sequence) preview = result.prediction;
        } catch (error) {
            if (requestSequence !== sequence) return;
            toast.error(`Smart select failed: ${getAnnotationPreviewErrorMessage(error)}`);
        } finally {
            if (requestSequence === sequence) isPending = false;
        }
    };

    const dropPreview = () => {
        sequence += 1;
        preview = null;
        isPending = false;
    };

    const reset = () => {
        dropPreview();
        points = [];
        box = null;
        clearReversibleActionsByGroupId(undoGroup);
    };

    const currentSampleId = $derived(getParams().sampleId);

    // Drops the prompts and requests of a previous sample, also while a save runs.
    $effect(() => {
        void currentSampleId;
        return reset;
    });

    // Keeps the preview while a save runs, so a failed save can be retried.
    const clear = () => {
        if (!isSaving) reset();
    };

    const rememberPrompt = () => {
        const previous = { points, box, preview };
        addReversibleAction({
            id: crypto.randomUUID(),
            groupId: undoGroup,
            description: 'Undo Smart select prompt',
            timestamp: new Date(),
            execute: () => {
                dropPreview();
                points = previous.points;
                box = previous.box;
                preview = previous.preview;
            }
        });
    };

    const addPoint = (point: SmartSelectPoint) => {
        if (isSaving || isPending) return;
        rememberPrompt();
        box = null;
        points = [...points, point];
        // The preview no longer matches the points, even if no new request starts.
        dropPreview();
        if (canInferFromPoints(points)) void infer({ points });
    };

    const selectBox = (value: NormalizedBox) => {
        if (isSaving || isPending) return;
        rememberPrompt();
        dropPreview();
        points = [];
        box = value;
        void infer({ boxes: [value] });
    };

    const save = async () => {
        const className = getParams().annotationClass;
        if (!preview || isSaving || isPending || !className?.trim()) return;
        // Saving ends prompt editing; saved annotations have their own Undo action.
        clearReversibleActionsByGroupId(undoGroup);
        isSaving = true;
        const { sampleId, saveAs, annotationSource, onSaved } = getParams();
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
        get box() {
            return box;
        },
        get preview() {
            return preview;
        },
        get canSave() {
            return (
                preview !== null && !isSaving && !isPending && !!getParams().annotationClass?.trim()
            );
        },
        get isSaving() {
            return isSaving;
        },
        get isPending() {
            return isPending;
        },
        addPoint,
        selectBox,
        clear,
        save
    };
};
