import type { AnnotationType } from '$lib/api/lightly_studio_local';
import type { BoundingBox } from '$lib/types';
import { getContext, setContext } from 'svelte';

export type AnnotationLabelContext = {
    // Selected annotation ID.
    annotationId?: string | null;
    currentAnnotationBoundingBox?: BoundingBox | null;
    lockedAnnotationIds?: Set<string>;
    isAnnotationLocked?: (annotationId?: string | null) => boolean;

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
    isOnAnnotationDetailsView?: boolean;
};

const CONTEXT_KEY = 'annotation-label';

export function createAnnotationLabelContext(
    initialValue: AnnotationLabelContext = {}
): AnnotationLabelContext {
    const context: AnnotationLabelContext = $state({
        lockedAnnotationIds: new Set<string>(),
        ...initialValue
    });

    setContext(CONTEXT_KEY, context);
    return context;
}

export function useAnnotationLabelContext(): {
    context: AnnotationLabelContext;
    setAnnotationId: (id: string | null) => void;
    setCurrentBoundingBox: (bbox: BoundingBox | null) => void;
    setAnnotationLabel: (label: string | null) => void;
    setAnnotationType: (type: AnnotationType | null) => void;
    setLastCreatedAnnotationId: (id: string | null) => void;
    setIsDrawing: (value: boolean) => void;
    setIsErasing: (value: boolean) => void;
    setIsDragging: (value: boolean) => void;
    setLockedAnnotationIds: (ids: Set<string>) => void;
    isAnnotationLocked: (annotationId?: string | null) => boolean;
} {
    const context = getContext<AnnotationLabelContext>(CONTEXT_KEY);

    if (!context) {
        throw new Error('AnnotationLabelContext not found');
    }

    function setAnnotationId(id: string | null) {
        context.annotationId = id;
    }

    function setCurrentBoundingBox(bbox: BoundingBox | null) {
        context.currentAnnotationBoundingBox = bbox;
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

    function setLockedAnnotationIds(ids: Set<string>) {
        context.lockedAnnotationIds = ids;
    }

    function isAnnotationLocked(annotationId?: string | null) {
        if (!annotationId) return false;
        return context.lockedAnnotationIds?.has(annotationId) ?? false;
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
        setCurrentBoundingBox,
        setAnnotationLabel,
        setAnnotationType,
        setLastCreatedAnnotationId,
        setIsDrawing,
        setIsErasing,
        setIsDragging,
        setLockedAnnotationIds,
        isAnnotationLocked
    };
}
