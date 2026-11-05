import {
    predictAnnotationClasses,
    type AnnotationClassPredictionView
} from '$lib/api/lightly_studio_local';
import { getContext, setContext } from 'svelte';

const TOP_COUNT = 3;
const CONTEXT_KEY = 'annotation-class-prediction';

type ClassPredictionState =
    | { status: 'hidden' }
    | { status: 'loading'; annotationId: string }
    | { status: 'ready'; annotationId: string; top: AnnotationClassPredictionView[] };

interface PredictParams {
    collectionId: string;
    annotationId: string;
}

interface AnnotationClassPrediction {
    readonly state: ClassPredictionState;
    predict(params: PredictParams): Promise<void>;
    hide(): void;
}

/**
 * Holds the class prediction of the annotation drawn last. A response for any other
 * annotation, or one that arrives after hide(), is dropped.
 */
export function createAnnotationClassPrediction(): AnnotationClassPrediction {
    let state = $state<ClassPredictionState>({ status: 'hidden' });
    // Increments on every predict() and hide(), so only the latest request may set the state.
    let requestCount = 0;

    async function predict({ collectionId, annotationId }: PredictParams): Promise<void> {
        const request = ++requestCount;
        state = { status: 'loading', annotationId };
        const top = await fetchTop({ collectionId, annotationId });
        if (request !== requestCount) return;
        state = top.length > 0 ? { status: 'ready', annotationId, top } : { status: 'hidden' };
    }

    function hide(): void {
        requestCount++;
        state = { status: 'hidden' };
    }

    return {
        get state() {
            return state;
        },
        predict,
        hide
    };
}

export function createAnnotationClassPredictionContext(): AnnotationClassPrediction {
    return setContext(CONTEXT_KEY, createAnnotationClassPrediction());
}

/** Returns undefined outside a view that enabled class prediction. */
export function useAnnotationClassPredictionContext(): AnnotationClassPrediction | undefined {
    return getContext<AnnotationClassPrediction | undefined>(CONTEXT_KEY);
}

async function fetchTop({
    collectionId,
    annotationId
}: PredictParams): Promise<AnnotationClassPredictionView[]> {
    try {
        const { data } = await predictAnnotationClasses({
            path: { collection_id: collectionId, annotation_id: annotationId }
        });
        const predictions = data ?? [];
        if (predictions.every((prediction) => prediction.score === 0)) return [];
        return predictions.slice(0, TOP_COUNT);
    } catch {
        return [];
    }
}
