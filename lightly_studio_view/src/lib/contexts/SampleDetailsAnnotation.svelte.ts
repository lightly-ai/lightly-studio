import type { AnnotationType } from '$lib/api/lightly_studio_local';
import { getContext, setContext } from 'svelte';

export type AnnotationLabelContext = {
    // Selected annotation ID.
    annotationId?: string | null;

    // Selected annotation label.
    annotationLabel?: string | null;

    // The annotation type selected via toolbar.
    annotationType?: AnnotationType | null;

    // The last annotation ID created.
    lastCreatedAnnotationId?: string | null;

    isDrawing?: boolean;
    isErasing?: boolean;
    isDragging?: boolean;

    // Check whether the page is an annotation details page.
    // This is usually determined in the parent component.
    isAnnotationDetails?: boolean;
};

const CONTEXT_KEY = 'annotation-label';

export function createAnnotationLabelContext(
    initialValue: AnnotationLabelContext = {}
): AnnotationLabelContext {
    const context: AnnotationLabelContext = $state(initialValue);

    setContext(CONTEXT_KEY, context);
    return context;
}

export function useAnnotationLabelContext(): {
    context: AnnotationLabelContext;
    setAnnotationId: (id: string | null) => void;
    setAnnotationLabel: (label: string | null) => void;
    setAnnotationType: (type: AnnotationType | null) => void;
    setLastCreatedAnnotationId: (id: string | null) => void;
    setIsDrawing: (value: boolean) => void;
    setIsErasing: (value: boolean) => void;
    setIsDragging: (value: boolean) => void;
} {
    const context = getContext<AnnotationLabelContext>(CONTEXT_KEY);

    if (!context) {
        throw new Error('AnnotationLabelContext not found');
    }

    function setAnnotationId(id: string | null) {
        context.annotationId = id;
    }

    function setAnnotationLabel(label: string | null) {
        context.annotationLabel = label;
    }

    function setAnnotationType(type: AnnotationType | null) {
        context.annotationType = type;
    }

    function setLastCreatedAnnotationId(id: string | null) {
        context.lastCreatedAnnotationId = id;
    }

    function setIsDrawing(value: boolean) {
        context.isDrawing = value;
    }

    function setIsErasing(value: boolean) {
        context.isErasing = value;
    }

    function setIsDragging(value: boolean) {
        context.isDragging = value;
    }

    return {
        context,
        setAnnotationId,
        setAnnotationLabel,
        setAnnotationType,
        setLastCreatedAnnotationId,
        setIsDrawing,
        setIsErasing,
        setIsDragging
    };
}
