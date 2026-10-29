import {
    deleteAnnotationSourceMutation,
    readAnnotationsOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';

interface Params {
    collectionId: string;
    source: { id: string; name: string };
    /** The annotation count loads only while the dialog is open. */
    open: boolean;
    onDeleted: () => void;
}

export const useDeleteAnnotationSource = (getParams: () => Params) => {
    const client = useQueryClient();
    const annotations = createQuery(() => {
        const { source, open } = getParams();
        return {
            ...readAnnotationsOptions({
                path: { collection_id: source.id },
                query: { cursor: 0, limit: 1 }
            }),
            enabled: open
        };
    });
    const mutation = createMutation(() => ({
        ...deleteAnnotationSourceMutation(),
        onSuccess: () => {
            const { source, onDeleted } = getParams();
            // A source shows up in grids, counts, plots and evaluations, so refetch everything.
            client.invalidateQueries();
            toast.success(`Deleted the annotation source “${source.name}”`);
            onDeleted();
        },
        onError: (error) => {
            const message =
                (error as { error?: string })?.error ??
                'Could not delete the annotation source. Try again.';
            toast.error(message);
        }
    }));
    const remove = () => {
        if (mutation.isPending) return;
        const { collectionId, source } = getParams();
        mutation.mutate({
            path: { collection_id: collectionId, annotation_collection_id: source.id }
        });
    };
    return {
        mutation,
        remove,
        annotationCount: () => annotations.data?.total_count
    };
};
