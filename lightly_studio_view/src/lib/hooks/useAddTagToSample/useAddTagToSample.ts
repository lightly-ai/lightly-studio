import { createTag, addSampleIdsToTagId } from '$lib/api/lightly_studio_local';
import type { TagView } from '$lib/services/types';
import { get, readonly, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';

interface Options {
    collectionId: string;
    sampleId: string;
    getTagKind: () => TagView['kind'];
    onRefetch: () => void;
    onTagsRefetch: () => void;
}

export function useAddTagToSample({
    collectionId,
    sampleId,
    getTagKind,
    onRefetch,
    onTagsRefetch
}: Options) {
    const _busy = writable(false);
    const busy = readonly(_busy);

    async function addExisting(tag: TagView) {
        if (get(_busy)) return;
        _busy.set(true);
        try {
            const response = await addSampleIdsToTagId({
                path: { collection_id: collectionId, tag_id: tag.tag_id },
                body: { sample_ids: [sampleId] }
            });
            if (response.error) throw new Error('assign tag failed');
        } catch {
            toast.error('Failed to add tag. Please try again.');
            return;
        } finally {
            _busy.set(false);
        }
        onRefetch();
    }

    async function createAndAdd(name: string) {
        const trimmed = name.trim();
        if (!trimmed || get(_busy)) return;
        _busy.set(true);
        try {
            const response = await createTag({
                path: { collection_id: collectionId },
                body: { name: trimmed, kind: getTagKind() }
            });
            if (response.error) throw new Error('create tag failed');
            if (response.data?.tag_id) {
                const addResponse = await addSampleIdsToTagId({
                    path: { collection_id: collectionId, tag_id: response.data.tag_id },
                    body: { sample_ids: [sampleId] }
                });
                if (addResponse.error) throw new Error('assign tag failed');
            }
        } catch {
            toast.error('Failed to add tag. Please try again.');
            return;
        } finally {
            _busy.set(false);
        }
        onTagsRefetch();
        onRefetch();
    }

    return { busy, addExisting, createAndAdd };
}
