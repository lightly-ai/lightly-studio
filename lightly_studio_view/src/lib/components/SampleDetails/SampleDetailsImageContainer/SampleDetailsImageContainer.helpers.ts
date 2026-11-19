import { isEqual } from 'lodash-es';
import type { AnnotationView } from '$lib/api/lightly_studio_local';

interface IsPanEnabledParams {
    isDrawing?: boolean;
    isErasing?: boolean;
    // Set by an assisted labeling tool that uses drags on the image.
    blocksPan: boolean;
}

export const isPanEnabled = ({ isDrawing, isErasing, blocksPan }: IsPanEnabledParams): boolean =>
    !(isDrawing || isErasing || blocksPan);

/**
 * Keeps the previous object for every annotation that did not change. TanStack cannot do
 * this here because `created_at` is a Date, so each refetch would redraw every annotation.
 */
export const reuseUnchangedAnnotations = (
    previous: AnnotationView[],
    next: AnnotationView[]
): AnnotationView[] => {
    const previousById = new Map(previous.map((annotation) => [annotation.sample_id, annotation]));
    return next.map((annotation) => {
        const old = previousById.get(annotation.sample_id);
        return old && isEqual(old, annotation) ? old : annotation;
    });
};

interface GetDrawerLabelParams {
    isAnnotationSelected: boolean;
    contextLabel: string | null | undefined;
    stickyClass: string | undefined;
}

/**
 * The class whose color the drawing tools use. A selected annotation keeps its class. Otherwise
 * the next annotation gets the sticky class, so the stroke shows that one.
 */
export const getDrawerLabel = ({
    isAnnotationSelected,
    contextLabel,
    stickyClass
}: GetDrawerLabelParams): string | null =>
    (isAnnotationSelected ? contextLabel : stickyClass) ?? null;
