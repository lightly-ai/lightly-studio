import {
    addSampleIdsToTagId,
    addSamplesToTagByFilter,
    createTag,
    removeSampleIdsFromTagId,
    type TagByFilterBody
} from '$lib/api/lightly_studio_local';
import type { TagView } from '$lib/services/types';
import { get, readonly, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { usePostHog } from '$lib/hooks/usePostHog';

type TagEventName = 'samples_tagged' | 'samples_untagged';

type SelectAllSnapshot = { filter: TagByFilterBody['filter']; size: number };

interface UseTagMutationsParams {
    collectionId: string;
    getTagKind: () => TagView['kind'];
    /** The samples the next mutation applies to. */
    getTargetIds: () => string[];
    /** Non-null only while the targets are still an unmodified select-all. */
    getSelectAllSnapshot: () => SelectAllSnapshot | null;
    getExistingTags: () => TagView[];
    /** Called after a successful mutation so the grid can refetch. */
    onSamplesRefetch: () => void;
    /** Called after a tag is created so tag lists pick it up. */
    onTagsRefetch: () => void;
}

/**
 * Assigns and removes tags for a set of target samples.
 *
 * Shared by the tag sidebar and the grid context menu so both apply tags the same
 * way — in particular the select-all shortcut that tags by filter instead of
 * sending a large id list.
 *
 * @param params The collection, reactive target getters, and refetch callbacks.
 * @returns A `busy` store plus the assign and remove actions.
 */
export function useTagMutations({
    collectionId,
    getTagKind,
    getTargetIds,
    getSelectAllSnapshot,
    getExistingTags,
    onSamplesRefetch,
    onTagsRefetch
}: UseTagMutationsParams) {
    const _busy = writable(false);
    const busy = readonly(_busy);
    const { trackEvent } = usePostHog();

    function trackTagEvent(event: TagEventName, properties: Record<string, unknown>) {
        try {
            trackEvent(event, {
                collection_id: collectionId,
                tag_kind: getTagKind(),
                ...properties
            });
        } catch (error) {
            console.error(`Failed to track ${event} event`, error);
        }
    }

    // Tag by filter when the selection is still an unmodified select-all (do not send
    // a potentially large ID list), else fall back to the ID-list path.
    function assignTargetsToTag(tagId: string, targetIds: string[]) {
        const snapshot = getSelectAllSnapshot();
        const isUnmodifiedSelectAll = snapshot != null && snapshot.size === targetIds.length;
        if (isUnmodifiedSelectAll) {
            return addSamplesToTagByFilter({
                path: { collection_id: collectionId, tag_id: tagId },
                body: { filter: snapshot.filter }
            });
        }
        return addSampleIdsToTagId({
            path: { collection_id: collectionId, tag_id: tagId },
            body: { sample_ids: targetIds }
        });
    }

    async function assignTag(tagId: string) {
        const targetIds = getTargetIds();
        if (!targetIds.length || get(_busy)) return;
        _busy.set(true);
        try {
            const response = await assignTargetsToTag(tagId, targetIds);
            if (response.error) throw new Error('assign tag failed');
            trackTagEvent('samples_tagged', {
                sample_count: targetIds.length,
                is_new_tag: false
            });
        } catch (error) {
            console.error('Failed to assign tag', error);
            toast.error('Failed to assign tag. Please try again.');
            return;
        } finally {
            _busy.set(false);
        }
        onTagsRefetch();
        onSamplesRefetch();
    }

    async function assignByName(name: string) {
        const trimmed = name.trim();
        const targetIds = getTargetIds();
        if (!trimmed || !targetIds.length || get(_busy)) return;

        const existingTag = getExistingTags().find(
            (tag) => tag.name.toLowerCase() === trimmed.toLowerCase()
        );
        if (existingTag) {
            await assignTag(existingTag.tag_id);
            return;
        }

        _busy.set(true);
        try {
            const createResponse = await createTag({
                path: { collection_id: collectionId },
                body: { name: trimmed, kind: getTagKind() }
            });
            if (createResponse.error || !createResponse.data?.tag_id) {
                toast.error('Failed to create tag. Please try again.');
                return;
            }
            const assignResponse = await assignTargetsToTag(createResponse.data.tag_id, targetIds);
            if (assignResponse.error) {
                toast.error('Failed to assign tag. Please try again.');
                return;
            }
            trackTagEvent('samples_tagged', {
                sample_count: targetIds.length,
                is_new_tag: true
            });
        } catch (error) {
            console.error('Failed to assign tag', error);
            toast.error('Failed to assign tag. Please try again.');
            return;
        } finally {
            _busy.set(false);
        }
        onTagsRefetch();
        onSamplesRefetch();
    }

    async function removeTag(tagId: string) {
        const targetIds = getTargetIds();
        if (!targetIds.length || get(_busy)) return;
        _busy.set(true);
        try {
            // There is no remove-by-filter endpoint, so a select-all removal sends the
            // materialized ids that useSelectAll already fetched into the selection.
            const response = await removeSampleIdsFromTagId({
                path: { collection_id: collectionId, tag_id: tagId },
                body: { sample_ids: targetIds }
            });
            if (response.error) throw new Error('remove tag failed');
            trackTagEvent('samples_untagged', { sample_count: targetIds.length });
        } catch (error) {
            console.error('Failed to remove tag', error);
            toast.error('Failed to remove tag. Please try again.');
            return;
        } finally {
            _busy.set(false);
        }
        onSamplesRefetch();
    }

    return { busy, assignTag, assignByName, removeTag };
}
