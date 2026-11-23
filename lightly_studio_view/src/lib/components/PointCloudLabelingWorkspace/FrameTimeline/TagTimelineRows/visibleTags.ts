import type { TickTagView } from '$lib/api/lightly_studio_local/types.gen';

/** How many frame tags show before the user picks their own. */
export const DEFAULT_VISIBLE_TAG_COUNT = 3;

/** The frame tags shown when the user has made no choice: the first ones in list order. */
export function getDefaultTagIds(tags: readonly TickTagView[]): string[] {
    return tags.slice(0, DEFAULT_VISIBLE_TAG_COUNT).map((tag) => tag.tag_id);
}

/** The frame tags the timeline lists. An explicit choice wins over the default. */
export function selectVisibleTags(
    tags: readonly TickTagView[],
    selection: readonly string[] | null
): TickTagView[] {
    const chosen = new Set(selection ?? getDefaultTagIds(tags));
    return tags.filter((tag) => chosen.has(tag.tag_id));
}
