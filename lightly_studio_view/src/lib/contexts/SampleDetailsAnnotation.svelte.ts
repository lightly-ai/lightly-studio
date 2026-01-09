import type { AnnotationType } from '$lib/api/lightly_studio_local';
import { getContext, setContext } from 'svelte';

export type AnnotationLabelContext = {
    // Selected annotation ID.
    annotationId?: string | null | undefined;

    // Selected annotation label.
    annotationLabel?: string | null | undefined;

    // The annotation type selected via toolbar.
    annotationType?: AnnotationType | null | undefined;

    // The last annotation ID created.
    lastCreatedAnnotationId?: string | null | undefined;

    isDrawing?: boolean;

    isErasing?: boolean;
};

const CONTEXT_KEY = 'annotation-label';

export function createAnnotationLabelContext(
    initiaValue: AnnotationLabelContext
): AnnotationLabelContext {
    const context: AnnotationLabelContext = $state(initiaValue);

    setContext(CONTEXT_KEY, context);
    return context;
}

export function useAnnotationLabelContext(): AnnotationLabelContext {
    const context = getContext<AnnotationLabelContext>(CONTEXT_KEY);

    if (!context) {
        throw new Error('AnnotationLabelContext not found');
    }

    return context;
}
