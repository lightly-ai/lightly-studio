import type { AnnotationType } from '$lib/api/lightly_studio_local';
import type { BoundingBox } from '$lib/types';
import { getContext, setContext } from 'svelte';

export type AnnotationLabelContext = {
    // Selected annotation ID.
    annotationId?: string | null;
    currentAnnotationBoundingBox?: BoundingBox | null;
    lockedAnnotationIds?: Set<string>;
    isAnnotationLocked?: (annotationId?: string | null) => boolean;

    // The class of the selected annotation. New annotations get the sticky class instead.
    annotationLabel?: string | null;

    // The source new annotations go to, or null while it is unknown or not picked. Set by
    // useAnnotationTarget only.
    annotationSource?: string | null;

    // Why new annotations must not be created right now, or null when they may: the sources
    // load, no source is picked among several, or the picked source is hidden. Set by
    // useAnnotationTarget only.
    annotationSourceBlockedReason?: string | null;

    // The sources whose annotations are all hidden on this sample. They can't be the target.
    // Set by useAnnotationTarget only.
    hiddenAnnotationSources?: string[];

    // A new source name typed on this page. It may be the target before the source exists.
    // Set by useSetTargetSource only.
    typedAnnotationSource?: string | null;

    // The annotation type selected via toolbar.
    annotationType?: AnnotationType | null;

    // The last annotation ID created.
    lastCreatedAnnotationId?: string | null;

    isDrawing?: boolean;
    isErasing?: boolean;
    isDragging?: boolean;
    isChangingBrushSize?: boolean;

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
    setIsChangingBrushSize: (value: boolean) => void;
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

    function setIsChangingBrushSize(value: boolean) {
        context.isChangingBrushSize = value;
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
        isAnnotationLocked,
        setIsChangingBrushSize
    };
}
