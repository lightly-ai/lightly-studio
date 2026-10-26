import {
    createAnnotationLabelMutation,
    deleteAnnotationLabelMutation,
    readAnnotationLabelsWithCountsOptions,
    updateAnnotationLabelMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { toast } from 'svelte-sonner';

// Lists the annotation classes of a dataset with their annotation counts, and adds,
// renames and deletes them.
export const useAnnotationClasses = (
    getParams: () => { collectionId: string; datasetId: string }
) => {
    const client = useQueryClient();
    const getPath = () => ({ path: { collection_id: getParams().collectionId } });
    const queryOptions = () => readAnnotationLabelsWithCountsOptions(getPath());
    const query = createQuery(queryOptions);

    // Classes belong to the dataset. The class pickers read them without counts, and
    // possibly through another collection, so refresh every class list.
    const onSettled = () =>
        Promise.all([
            client.invalidateQueries({ queryKey: queryOptions().queryKey }),
            client.invalidateQueries({ queryKey: [{ _id: 'readAnnotationLabels' }] })
        ]);
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
        // Deleting a class also deletes its annotations, so all cached data can be stale.
        onSettled: () => client.invalidateQueries(),
        onError: onErrorWith('Could not delete the annotation class.')
    }));

    const addClass = (name: string) =>
        createMut.mutateAsync({
            path: { collection_id: getParams().collectionId },
            body: { annotation_label_name: name }
        });
    // Custom colors are stored by class name, so a rename moves the color to the new name.
    const { getCustomColor, setCustomColor, deleteCustomColor } = useCustomLabelColors();
    const renameClass = async (labelId: string, oldName: string, name: string) => {
        await updateMut.mutateAsync({
            path: { label_id: labelId },
            body: { dataset_id: getParams().datasetId, annotation_label_name: name }
        });
        const customColor = getCustomColor(oldName);
        if (customColor) {
            setCustomColor(name, customColor.color, customColor.alpha);
            deleteCustomColor(oldName);
        }
    };
    const deleteClass = (labelId: string) => deleteMut.mutateAsync({ path: { label_id: labelId } });

    return { query, addClass, renameClass, deleteClass };
};
