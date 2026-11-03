import { toast } from 'svelte-sonner';
import type { AnnotationLabelContext } from './SampleDetailsAnnotation.svelte';

export const MISSING_ANNOTATION_SOURCE_MESSAGE =
    'Pick a source with the pencil in the Annotations panel before adding annotations.';

/**
 * Returns true, and tells the user why, when a new annotation must not be created because there
 * are several annotation sources and none is picked. Call it before creating an annotation.
 */
export function isAnnotationSourceMissing(
    context: Pick<AnnotationLabelContext, 'annotationSourceMissing'>
): boolean {
    if (!context.annotationSourceMissing) return false;
    toast.error(MISSING_ANNOTATION_SOURCE_MESSAGE);
    return true;
}
