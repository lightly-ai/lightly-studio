import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { getTickDetailsSequenceQueryKey, useUpdateAnnotationsMutation } from '$lib/hooks';
import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
import type { AnnotationIdMap } from '../cuboidUndo';

interface Params {
    getCollectionId: () => string | undefined;
    getDatasetId: () => string;
    getSequenceId: () => string;
    onUpdated: () => Promise<unknown>;
    /** The persisted annotations of the active tick. */
    getAnnotations: () => readonly AnnotationView[];
    annotationIds: AnnotationIdMap;
    addReversibleAction: (action: ReversibleAction) => void;
}

interface UseUpdateCuboidClassReturn {
    handleLabelChange: (
        annotationId: string,
        className: string,
        annotationSourceId: string
    ) => Promise<void>;
}

/**
 * Saves an annotation class, refreshes all cached ticks for its object track, and adds the undo
 * of the change.
 */
export function useUpdateCuboidClass({
    getCollectionId,
    getDatasetId,
    getSequenceId,
    onUpdated,
    getAnnotations,
    annotationIds,
    addReversibleAction
}: Params): UseUpdateCuboidClassReturn {
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        getCollectionId: () => getCollectionId() ?? ''
    });
    const queryClient = useQueryClient();
    // Saved classes that the persisted annotations do not show yet, because a refresh failed.
    const unrefreshedClassNames = new Map<string, string>();

    async function refreshAfterClassChange(annotationSourceId: string): Promise<void> {
        void queryClient.invalidateQueries({
            queryKey: getTickDetailsSequenceQueryKey({
                datasetId: getDatasetId(),
                sequenceId: getSequenceId()
            })
        });
        void queryClient.invalidateQueries({
            queryKey: readAnnotationLabelsOptions({
                path: { collection_id: annotationSourceId }
            }).queryKey
        });
        try {
            await onUpdated();
            unrefreshedClassNames.clear();
        } catch {
            toast.error(
                'Annotation class updated, but the workspace could not refresh. Please try again.'
            );
        }
    }

    async function saveClasses(
        inputs: AnnotationUpdateInput[],
        collectionId: string
    ): Promise<void> {
        await updateAnnotations(inputs, collectionId);
        for (const { annotation_id, label_name } of inputs) {
            if (label_name) unrefreshedClassNames.set(annotation_id, label_name);
        }
    }

    function findSavedAnnotation(annotationId: string): AnnotationView | undefined {
        const annotation = getAnnotations().find(({ sample_id }) => sample_id === annotationId);
        const unrefreshedClassName = unrefreshedClassNames.get(annotationId);
        if (!annotation || !unrefreshedClassName) return annotation;
        return {
            ...annotation,
            annotation_label: {
                ...annotation.annotation_label,
                annotation_label_name: unrefreshedClassName
            }
        };
    }

    function addUndo(
        previousAnnotation: AnnotationView,
        annotationSourceId: string,
        collectionId: string
    ): void {
        addAnnotationLabelChangeToUndoStack({
            annotations: [previousAnnotation],
            collectionId,
            addReversibleAction,
            updateAnnotations: (inputs) =>
                saveClasses(
                    inputs.map((input) => ({
                        ...input,
                        annotation_id: annotationIds.resolve(input.annotation_id)
                    })),
                    collectionId
                ),
            refresh: () => void refreshAfterClassChange(annotationSourceId)
        });
    }

    async function handleLabelChange(
        annotationId: string,
        className: string,
        annotationSourceId: string
    ): Promise<void> {
        const previousAnnotation = findSavedAnnotation(annotationId);
        // The undo uses the collection of the change, also after the workspace changes it.
        const collectionId = getCollectionId() ?? '';
        try {
            await saveClasses(
                [
                    {
                        annotation_id: annotationId,
                        collection_id: collectionId,
                        label_name: className
                    }
                ],
                collectionId
            );
        } catch (error) {
            toast.error('Failed to update annotation class. Please try again.');
            throw error;
        }
        const classChanged =
            previousAnnotation?.annotation_label.annotation_label_name !== className;
        if (previousAnnotation && classChanged)
            addUndo(previousAnnotation, annotationSourceId, collectionId);
        await refreshAfterClassChange(annotationSourceId);
    }

    return { handleLabelChange };
}
