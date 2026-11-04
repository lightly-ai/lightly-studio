import {
    createAnnotationCollectionMutation,
    readAnnotationCollectionsWithCountsOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { useRenameAnnotationSource } from '$lib/components/AnnotationCollectionsMenu/useRenameAnnotationSource/useRenameAnnotationSource';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useDefaultSource } from '$lib/hooks/useDefaultSource/useDefaultSource';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { toast } from 'svelte-sonner';

interface UseAnnotationSourcesParams {
    collectionId: string;
}

// Lists the annotation sources of a collection with their annotation counts, and adds and
// renames them. Deleting goes through the DeleteAnnotationSource dialog.
export const useAnnotationSources = (getParams: () => UseAnnotationSourcesParams) => {
    const client = useQueryClient();
    const getPath = () => ({ path: { collection_id: getParams().collectionId } });
    const query = createQuery(() => ({
        ...readAnnotationCollectionsWithCountsOptions(getPath()),
        enabled: !!getParams().collectionId
    }));

    const createMut = createMutation(() => ({
        ...createAnnotationCollectionMutation(),
        // Sources show in filters, pickers and the annotations panel. Refresh every query.
        onSettled: () => client.invalidateQueries(),
        onError: (error) => {
            const detail = (error as unknown as { detail?: string })?.detail;
            toast.error(detail ?? 'Could not add the annotation source.');
        }
    }));
    const addSource = (name: string) => createMut.mutateAsync({ ...getPath(), body: { name } });

    // Custom colors and the pencil target are stored by name, so a rename moves them.
    const { getCustomColor, setCustomColor, deleteCustomColor } = useCustomLabelColors();
    const { renameLastAnnotationSource } = useGlobalStorage();
    const { renameDefaultSource } = useDefaultSource();
    const { rename, renamingId } = useRenameAnnotationSource(() => ({
        collectionId: getParams().collectionId,
        sources: (query.data ?? []).map((s) => ({ id: s.collection_id, name: s.name })),
        onRenamed: (source, newName) => {
            const customColor = getCustomColor(source.name);
            if (customColor) {
                setCustomColor(newName, customColor.color, customColor.alpha);
                deleteCustomColor(source.name);
            }
            renameLastAnnotationSource(getParams().collectionId, source.name, newName);
            renameDefaultSource(getParams().collectionId, source.name, newName);
        }
    }));

    return { query, addSource, renameSource: rename, renamingId };
};
