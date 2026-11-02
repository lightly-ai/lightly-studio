import { createQuery } from '@tanstack/svelte-query';
import type { SelectionTagCountsBody } from '$lib/api/lightly_studio_local';
import { countSelectionTagsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

interface UseSelectionTagCountsParams {
    collection_id: string;
    selection: SelectionTagCountsBody;
    enabled: boolean;
}

/** Number of selected samples per tag ID. Tags no selected sample carries are missing. */
export const useSelectionTagCounts = (getParams: () => UseSelectionTagCountsParams) => {
    const query = createQuery(() => {
        const { collection_id, selection, enabled } = getParams();
        return {
            ...countSelectionTagsOptions({ path: { collection_id }, body: selection }),
            enabled,
            select: (data: { tag_id: string; sample_count: number }[]) =>
                new Map(data.map((entry) => [entry.tag_id, entry.sample_count]))
        };
    });
    return { query };
};
