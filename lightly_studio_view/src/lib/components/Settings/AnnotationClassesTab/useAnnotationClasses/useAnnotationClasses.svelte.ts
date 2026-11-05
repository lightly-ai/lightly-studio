import {
    createAnnotationLabelMutation,
    deleteAnnotationLabelMutation,
    readAnnotationLabelsWithCountsOptions,
    readCollectionHierarchyOptions,
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
import { useGlobalStorage, useRecentClasses } from '$lib/hooks';
import { toast } from 'svelte-sonner';

interface UseAnnotationClassesParams {
    collectionId: string;
    datasetId: string;
}

interface UseAnnotationClassesReturn {
    query: CreateQueryResult<ReadAnnotationLabelsWithCountsResponse>;
    addClass: (name: string) => Promise<CreateAnnotationLabelResponse>;
    renameClass: (labelId: string, oldName: string, name: string) => Promise<void>;
    deleteClass: (labelId: string, name: string) => Promise<unknown>;
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
    // The class for new annotations and the recent classes are stored by class name, so a
    // rename moves them to the new name and a delete forgets the class.
    const { renameLastAnnotationLabel, removeLastAnnotationLabel } = useGlobalStorage();
    const { renameRecentClass, removeRecentClass } = useRecentClasses();
    // Classes belong to the dataset, but the class for new annotations and the recent classes
    // are stored per collection. Update them in every collection of the dataset.
    const forEachDatasetCollection = async (update: (collectionId: string) => void) => {
        const { collectionId, datasetId } = getParams();
        let collectionIds = [collectionId];
        try {
            const hierarchy = await client.fetchQuery(
                readCollectionHierarchyOptions({ path: { collection_id: datasetId } })
            );
            collectionIds = [...new Set([collectionId, ...hierarchy.map((c) => c.collection_id)])];
        } catch {
            // Without the hierarchy, update the current collection only.
        }
        collectionIds.forEach(update);
    };
    const renameClass = async (labelId: string, oldName: string, name: string) => {
        await updateMut.mutateAsync({
            path: { label_id: labelId },
            body: { dataset_id: getParams().datasetId, annotation_label_name: name }
        });
        if (oldName === name) return;
        await forEachDatasetCollection((collectionId) => {
            renameLastAnnotationLabel(collectionId, oldName, name);
            renameRecentClass(collectionId, oldName, name);
        });
    };
    const deleteClass = async (labelId: string, name: string) => {
        const result = await deleteMut.mutateAsync({ path: { label_id: labelId } });
        await forEachDatasetCollection((collectionId) => {
            removeLastAnnotationLabel(collectionId, name);
            removeRecentClass(collectionId, name);
        });
        return result;
    };

    return { query, addClass, renameClass, deleteClass };
};
