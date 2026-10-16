import { derived } from 'svelte/store';
import { useTags } from '$lib/hooks';
import { useTagExclusions } from '$lib/hooks/useTagExclusions';
import type { GroupFilter } from '$lib/api/lightly_studio_local';

export function useGroupTagFilter(collectionId: string) {
    const { tags, tagsSelected } = useTags({ collection_id: collectionId });
    const { excludedTagIds } = useTagExclusions(collectionId);
    return derived(
        [tags, tagsSelected, excludedTagIds],
        ([$tags, $selected, $excluded]): GroupFilter => ({
            filter_type: 'group',
            sample_filter: { tag_ids: [...$selected].filter((id) => !$excluded.has(id)) },
            excluded_tag_ids: $tags
                .filter((tag) => $excluded.has(tag.tag_id))
                .map((tag) => tag.tag_id)
        })
    );
}
