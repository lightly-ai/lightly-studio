import { untrack } from 'svelte';
import { get, readonly, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { loadImageBitmap } from '$lib/browserInference';
import { useBrowserModels, useSaveAnnotationPreviews } from '$lib/hooks';
import { runBatchAutoLabel } from './runBatchAutoLabel';

interface BatchState {
    status: 'idle' | 'running' | 'finished' | 'stopped';
    total: number;
    done: number;
    annotationCount: number;
    failedCount: number;
    modelId: string | null;
}

interface StartParams {
    sampleIds: string[];
    modelId: string;
    threshold: number;
    classNames: string[];
}

const IDLE_STATE: BatchState = {
    status: 'idle',
    total: 0,
    done: 0,
    annotationCount: 0,
    failedCount: 0,
    modelId: null
};

// Module-level, so the dock shows the run on every page of the collection.
const batchState = writable<BatchState>(IDLE_STATE);

// Runs a browser model on many samples and saves the annotations into a source named after
// the model. Leaving the collection or closing the tab stops the run.
export const useBatchAutoLabel = (params: {
    getCollectionId: () => string;
    getDatasetId: () => string;
}) => {
    const { getDetector } = useBrowserModels();
    // Fixed at start, so a run never saves into a collection that the user opened later.
    let runCollectionId = '';
    let runDatasetId = '';
    const { saveAnnotationPreviews } = useSaveAnnotationPreviews({
        getCollectionId: () => runCollectionId,
        getDatasetId: () => runDatasetId
    });
    let controller: AbortController | null = null;

    const stop = () => controller?.abort();

    const start = async ({ sampleIds, modelId, threshold, classNames }: StartParams) => {
        if (controller) return;
        runCollectionId = params.getCollectionId();
        runDatasetId = params.getDatasetId();
        controller = new AbortController();
        batchState.set({ ...IDLE_STATE, status: 'running', total: sampleIds.length, modelId });
        window.addEventListener('beforeunload', warnBeforeUnload);
        try {
            const detector = await getDetector(modelId);
            await runBatchAutoLabel({
                sampleIds,
                classNames: new Set(classNames),
                signal: controller.signal,
                detect: async (sampleId) => {
                    const image = await loadImageBitmap(sampleId, detector.inputSize);
                    return detector.detect(image.bitmap, image.original, threshold);
                },
                save: (sampleId, previews) =>
                    saveAnnotationPreviews({
                        sampleId,
                        saveAs: 'box',
                        annotationSource: modelId,
                        previews: previews.map((preview) => ({
                            preview,
                            className: preview.class_name
                        })),
                        onPreviewSaved: () => {}
                    }),
                onProgress: (progress) => batchState.update((state) => ({ ...state, ...progress }))
            });
        } catch (error) {
            toast.error(`Could not auto-label the images: ${String(error)}`);
        } finally {
            const status = controller.signal.aborted ? 'stopped' : 'finished';
            batchState.update((state) => ({ ...state, status }));
            window.removeEventListener('beforeunload', warnBeforeUnload);
            controller = null;
        }
    };

    const reset = () => {
        if (get(batchState).status !== 'running') batchState.set(IDLE_STATE);
    };

    // The layout stays mounted across collections, so a new collection ID stops the run.
    $effect(() => {
        params.getCollectionId();
        untrack(stop);
    });
    $effect(() => () => stop());

    return { state: readonly(batchState), start, stop, reset };
};

const warnBeforeUnload = (event: BeforeUnloadEvent) => event.preventDefault();
