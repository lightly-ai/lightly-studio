import { deleteAnnotationSourceMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { useGlobalStorage, useInvalidateAnnotationSourceQueries } from '$lib/hooks';
import { getApiErrorMessage } from '$lib/utils';
import { toast } from 'svelte-sonner';

interface Params {
    /** The collection that owns the annotation sources. */
    collectionId: string;
    source: { id: string; name: string };
    onDeleted: () => void;
}

export const useDeleteAnnotationSource = (getParams: () => Params) => {
    const invalidateAnnotationSourceQueries = useInvalidateAnnotationSourceQueries();
    const { removeLastAnnotationSource } = useGlobalStorage();

    const mutation = createMutation(() => ({
        ...deleteAnnotationSourceMutation(),
        onSuccess: () => {
            const { collectionId, source, onDeleted } = getParams();
            // The target is stored by name. Forget it, so the next annotation does not
            // re-create the deleted source.
            removeLastAnnotationSource(collectionId, source.name);
            invalidateAnnotationSourceQueries(collectionId);
            toast.success(`Deleted the annotation source “${source.name}”`);
            onDeleted();
        },
        onError: (error) => {
            toast.error(
                getApiErrorMessage(error, 'Could not delete the annotation source. Try again.')
            );
        }
    }));
    const remove = () => {
        if (mutation.isPending) return;
        const { collectionId, source } = getParams();
        mutation.mutate({
            path: { collection_id: collectionId, annotation_collection_id: source.id }
        });
    };
    return { mutation, remove };
};
