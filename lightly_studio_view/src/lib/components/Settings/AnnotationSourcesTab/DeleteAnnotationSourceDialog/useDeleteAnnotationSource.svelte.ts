import { deleteAnnotationSourceMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { useGlobalStorage, useInvalidateAnnotationSourceQueries } from '$lib/hooks';
import { getApiErrorMessage } from '$lib/utils';
import { toast } from 'svelte-sonner';

interface Params {
    /** The collection that owns the annotation sources. */
    collectionId: string;
    source: { id: string; name: string };
    /** Awaited before the refresh, so a navigation it starts completes first. */
    onDeleted: () => void | Promise<void>;
}

export const useDeleteAnnotationSource = (getParams: () => Params) => {
    const invalidateAnnotationSourceQueries = useInvalidateAnnotationSourceQueries();
    const { removeLastAnnotationSource } = useGlobalStorage();
    // The params of the request in flight. The params can change before it ends, for example
    // when the user opens another dataset, and the cleanup belongs to the deleted source.
    let request: Params | undefined;

    const mutation = createMutation(() => ({
        ...deleteAnnotationSourceMutation(),
        onSuccess: async () => {
            if (!request) return;
            const { collectionId, source, onDeleted } = request;
            // The target is stored by name. Forget it, so the next annotation does not
            // re-create the deleted source.
            removeLastAnnotationSource(collectionId, source.name);
            toast.success(`Deleted the annotation source “${source.name}”`);
            // The annotations grid of the deleted source can still be on screen with its
            // queries active. Leave it first, so the refresh below does not refetch a
            // collection the API no longer has.
            await onDeleted();
            invalidateAnnotationSourceQueries(collectionId);
        },
        onError: (error) => {
            toast.error(
                getApiErrorMessage(error, 'Could not delete the annotation source. Try again.')
            );
        }
    }));
    const remove = () => {
        if (mutation.isPending) return;
        request = getParams();
        const { collectionId, source } = request;
        mutation.mutate({
            path: { collection_id: collectionId, annotation_collection_id: source.id }
        });
    };
    return { mutation, remove };
};
