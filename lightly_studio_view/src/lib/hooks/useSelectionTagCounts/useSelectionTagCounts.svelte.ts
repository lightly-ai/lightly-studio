import { createQuery } from '@tanstack/svelte-query';
import { countTagsForSelectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { SelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';

interface UseSelectionTagCountsParams {
    collectionId: string;
    target: SelectionTarget;
    enabled?: boolean;
}

/**
 * How many selected items carry each tag, as a map from tag ID to count. Tags no selected
 * item carries are missing. The target is part of the query key, so counts refetch when the
 * selection changes.
 */
export const useSelectionTagCounts = (getParams: () => UseSelectionTagCountsParams) => {
    const query = createQuery(() => {
        const { collectionId, target, enabled = true } = getParams();
        return {
            ...countTagsForSelectionOptions({
                path: { collection_id: collectionId },
                body:
                    target.kind === 'filter'
                        ? { filter: target.filter }
                        : { sample_ids: target.ids }
            }),
            enabled,
            select: (data: { tag_id: string; count: number }[]) =>
                new Map(data.map((entry) => [entry.tag_id, entry.count]))
        };
    });
    return { query };
};
