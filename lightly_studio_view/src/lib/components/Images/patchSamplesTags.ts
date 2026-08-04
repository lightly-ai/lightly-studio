import type { InfiniteData } from '@tanstack/svelte-query';
import type { ImageView, ReadImagesResponse } from '$lib/api/lightly_studio_local';

interface PatchSamplesTagsParams {
    sampleIds: string[];
    tag: ImageView['tags'][number];
    action: 'add' | 'remove';
}

/**
 * Applies a tag change to the cached image pages so the grid reflects it immediately.
 *
 * `ImageView.tags` is embedded in each page, and the context menu reads its
 * checkbox state straight from it. Without this patch the state would lag a full
 * round-trip plus a refetch of every loaded page, inviting a contradictory second
 * click. Adding is idempotent so a re-run cannot duplicate a tag.
 *
 * @param data The cached infinite-query pages, or undefined when nothing is cached.
 * @param params The affected samples, the tag, and whether to add or remove it.
 * @returns New page data with the tag applied, or `data` untouched when nothing matched.
 */
export function patchSamplesTags(
    data: InfiniteData<ReadImagesResponse> | undefined,
    { sampleIds, tag, action }: PatchSamplesTagsParams
): InfiniteData<ReadImagesResponse> | undefined {
    if (!data) return data;

    const targetIds = new Set(sampleIds);

    return {
        ...data,
        pages: data.pages.map((page) => ({
            ...page,
            data: page.data.map((sample) =>
                targetIds.has(sample.sample_id) ? patchSampleTags(sample, tag, action) : sample
            )
        }))
    };
}

function patchSampleTags(
    sample: ImageView,
    tag: ImageView['tags'][number],
    action: 'add' | 'remove'
): ImageView {
    const hasTag = sample.tags.some((existing) => existing.tag_id === tag.tag_id);

    if (action === 'add') {
        return hasTag ? sample : { ...sample, tags: [...sample.tags, tag] };
    }
    return hasTag
        ? { ...sample, tags: sample.tags.filter((existing) => existing.tag_id !== tag.tag_id) }
        : sample;
}
