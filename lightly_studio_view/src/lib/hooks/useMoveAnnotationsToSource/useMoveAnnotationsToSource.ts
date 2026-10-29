import { moveAnnotations } from '$lib/api/lightly_studio_local';
import { useQueryClient } from '@tanstack/svelte-query';
import { get, readonly, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';

interface MoveToSourceInput {
    /** The collection that owns the annotation sources. */
    collectionId: string;
    annotationIds: string[];
    sourceName: string;
}

const FALLBACK_ERROR = 'Could not move the annotations. Try again.';

/** Moves annotations to an annotation source, which is created if it does not exist. */
export const useMoveAnnotationsToSource = () => {
    const client = useQueryClient();
    const isPending = writable(false);

    const moveToSource = async ({
        collectionId,
        annotationIds,
        sourceName
    }: MoveToSourceInput): Promise<boolean> => {
        if (get(isPending) || annotationIds.length === 0) return false;
        isPending.set(true);
        try {
            const { data, error } = await moveAnnotations({
                path: { collection_id: collectionId },
                body: {
                    annotation_ids: annotationIds,
                    target_annotation_collection_name: sourceName
                }
            });
            if (!data) {
                toast.error((error as { error?: string } | undefined)?.error ?? FALLBACK_ERROR);
                return false;
            }
            // A move changes grids, counts, sources, plots and evaluations, so refetch everything.
            client.invalidateQueries();
            const noun = data.moved_count === 1 ? 'annotation' : 'annotations';
            toast.success(`Moved ${data.moved_count} ${noun} to “${sourceName}”`);
            return true;
        } catch {
            toast.error(FALLBACK_ERROR);
            return false;
        } finally {
            isPending.set(false);
        }
    };

    return { moveToSource, isPending: readonly(isPending) };
};
