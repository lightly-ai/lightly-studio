import { createTag, addSampleIdsToTagId } from '$lib/api/lightly_studio_local';
import type { TagView } from '$lib/services/types';
import { toast } from 'svelte-sonner';

interface TagItem {
    tag_id?: string;
    name: string;
}

interface Options {
    collectionId: string;
    sampleId: string;
    getTagKind: () => TagView['kind'];
    getTags: () => TagItem[];
    getAllCollectionTags: () => TagView[];
    onRefetch: () => void;
    onTagsRefetch: () => void;
}

export function useAddTagToSample({
    collectionId,
    sampleId,
    getTagKind,
    getTags,
    getAllCollectionTags,
    onRefetch,
    onTagsRefetch
}: Options) {
    let busy = $state(false);

    const options = $derived(
        getAllCollectionTags().filter(
            (t) => !getTags().some((existing) => existing.tag_id === t.tag_id)
        )
    );

    async function addExisting(tag: TagView) {
        busy = true;
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
            busy = false;
        }
        onRefetch();
    }

    async function createAndAdd(name: string) {
        const trimmed = name.trim();
        if (!trimmed) return;
        busy = true;
        try {
            const response = await createTag({
                path: { collection_id: collectionId },
                body: { name: trimmed, description: `${trimmed} description`, kind: getTagKind() }
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
            busy = false;
        }
        onTagsRefetch();
        onRefetch();
    }

    return {
        get busy() {
            return busy;
        },
        get options() {
            return options;
        },
        addExisting,
        createAndAdd
    };
}
