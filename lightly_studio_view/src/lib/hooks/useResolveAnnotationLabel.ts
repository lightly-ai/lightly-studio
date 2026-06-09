import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { toast } from 'svelte-sonner';
import { useGlobalStorage } from './useGlobalStorage';

export function useResolveAnnotationLabel({
    collectionId,
    requestLabel
}: {
    collectionId: string;
    /** Called when no label is currently selected. Should show a class-picker and resolve with
     *  the chosen class, or null if the user cancelled. */
    requestLabel?: () => Promise<{ label: string } | null>;
}) {
    const { updateLastAnnotationLabel } = useGlobalStorage();
    const { context: annotationLabelContext, setAnnotationLabel } = useAnnotationLabelContext();

    const resolveAnnotationLabel = async (): Promise<string | null> => {
        if (annotationLabelContext.annotationLabel) {
            return annotationLabelContext.annotationLabel;
        }

        const result = requestLabel ? await requestLabel() : null;
        if (!result?.label) {
            toast.error('Please select a class before creating an annotation');
            return null;
        }

        setAnnotationLabel(result.label);
        updateLastAnnotationLabel(collectionId, result.label);
        return result.label;
    };

    return { resolveAnnotationLabel };
}
