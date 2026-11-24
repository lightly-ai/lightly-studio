import type { TagView } from '$lib/services/types';
import type { TagItem } from '../types';

const normalize = (name: string) => name.trim().toLowerCase();

/** The collection's tags that are not on the sample yet. Names match case-insensitively. */
export const getAddableTags = (
    collectionTags: TagView[],
    attached: readonly TagItem[]
): TagView[] =>
    collectionTags.filter(
        (tag) =>
            !attached.some(
                (existing) =>
                    existing.tag_id === tag.tag_id ||
                    normalize(existing.name) === normalize(tag.name)
            )
    );

export const getAttachedTagNames = (attached: readonly TagItem[]): Set<string> =>
    new Set(attached.map((tag) => normalize(tag.name)));

export type TagSelection =
    | { kind: 'attached' }
    | { kind: 'existing'; tag: TagView }
    | { kind: 'new'; name: string };

/** What picking `name` means: a tag already on the sample, an existing tag, or a new one. */
export const resolveTagSelection = (
    name: string,
    addableTags: TagView[],
    attachedTagNames: Set<string>
): TagSelection => {
    const trimmed = name.trim();
    const normalized = normalize(trimmed);
    if (attachedTagNames.has(normalized)) return { kind: 'attached' };
    const existing = addableTags.find((tag) => normalize(tag.name) === normalized);
    return existing ? { kind: 'existing', tag: existing } : { kind: 'new', name: trimmed };
};
