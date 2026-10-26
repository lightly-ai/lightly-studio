import {
    createAnnotationLabelMutation,
    deleteAnnotationLabelMutation,
    readAnnotationLabelsOptions,
    updateAnnotationLabelMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';

// Lists the annotation classes of a dataset and adds, renames and deletes them.
export const useAnnotationClasses = (
    getParams: () => { collectionId: string; datasetId: string }
) => {
    const client = useQueryClient();
    const getQueryOptions = () =>
        readAnnotationLabelsOptions({ path: { collection_id: getParams().collectionId } });
    const query = createQuery(() => getQueryOptions());

    const onSettled = () => client.invalidateQueries({ queryKey: getQueryOptions().queryKey });
    const onErrorWith = (message: string) => () => toast.error(message);
    const createMut = createMutation(() => ({
        ...createAnnotationLabelMutation(),
        onSettled,
        onError: onErrorWith('Could not add the annotation class.')
    }));
    const updateMut = createMutation(() => ({
        ...updateAnnotationLabelMutation(),
        onSettled,
        onError: onErrorWith('Could not rename the annotation class.')
    }));
    const deleteMut = createMutation(() => ({
        ...deleteAnnotationLabelMutation(),
        onSettled,
        onError: onErrorWith(
            'Could not delete the annotation class. Annotations of this class must be deleted first.'
        )
    }));

    const addClass = (name: string) =>
        createMut.mutateAsync({
            path: { collection_id: getParams().collectionId },
            body: { annotation_label_name: name }
        });
    const renameClass = (labelId: string, name: string) =>
        updateMut.mutateAsync({
            path: { label_id: labelId },
            body: { dataset_id: getParams().datasetId, annotation_label_name: name }
        });
    const deleteClass = (labelId: string) => deleteMut.mutateAsync({ path: { label_id: labelId } });

    return { query, addClass, renameClass, deleteClass };
};
