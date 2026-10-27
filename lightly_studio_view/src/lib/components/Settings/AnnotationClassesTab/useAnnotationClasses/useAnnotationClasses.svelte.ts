import {
    createAnnotationLabelMutation,
    deleteAnnotationLabelMutation,
    readAnnotationLabelsWithCountsOptions,
    updateAnnotationLabelMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    CreateAnnotationLabelResponse,
    ReadAnnotationLabelsWithCountsResponse
} from '$lib/api/lightly_studio_local/types.gen';
import {
    createMutation,
    createQuery,
    useQueryClient,
    type CreateQueryResult
} from '@tanstack/svelte-query';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { toast } from 'svelte-sonner';

interface UseAnnotationClassesParams {
    collectionId: string;
    datasetId: string;
}

interface UseAnnotationClassesReturn {
    query: CreateQueryResult<ReadAnnotationLabelsWithCountsResponse>;
    addClass: (name: string) => Promise<CreateAnnotationLabelResponse>;
    renameClass: (labelId: string, oldName: string, name: string) => Promise<void>;
    deleteClass: (labelId: string) => Promise<unknown>;
}

// Lists the annotation classes of a dataset with their annotation counts, and adds,
// renames and deletes them.
export const useAnnotationClasses = (
    getParams: () => UseAnnotationClassesParams
): UseAnnotationClassesReturn => {
    const client = useQueryClient();
    const getPath = () => ({ path: { collection_id: getParams().collectionId } });
    const queryOptions = () => readAnnotationLabelsWithCountsOptions(getPath());
    const query = createQuery(() => ({
        ...queryOptions(),
        enabled: !!getParams().collectionId
    }));

    // Classes belong to the dataset and are shown in many places: class pickers, the
    // sidebar class filter and annotation views. Refresh every cached query.
    const onSettled = () => client.invalidateQueries();
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
