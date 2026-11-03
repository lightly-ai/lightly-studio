import { toast } from 'svelte-sonner';
import type { AnnotationLabelContext } from './SampleDetailsAnnotation.svelte';

/**
 * Returns true, and tells the user why, when a new annotation must not be created: no source
 * is picked among several, or the picked source is hidden. Call it before creating an annotation.
 */
export function isAnnotationSourceBlocked(
    context: Pick<AnnotationLabelContext, 'annotationSourceBlockedReason'>
): boolean {
    if (!context.annotationSourceBlockedReason) return false;
    toast.error(context.annotationSourceBlockedReason);
    return true;
}
