import type { TagView as Tag, TagKind } from '$lib/services/types';
import { derived, get, readonly, writable, type Readable } from 'svelte/store';
import { readTags } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '../useGlobalStorage';

interface UseTagsOptions {
    collection_id: string;
    kind?: TagKind[];
}

interface UseTagsReturn {
    tags: Readable<Tag[]>;
    tagsSelected: Readable<Set<string>>;
    clearTagsSelected: () => void;
    loadTags: () => void;
    tagSelectionToggle: (tagId: string) => void;
    isLoading: Readable<boolean>;
    error: Readable<Error | null>;
}

const tagsSelectedByCollection = writable<Record<string, Set<string>>>({});
const tagRequestsByCollection = new Map<string, Promise<void>>();

export function useTags(options: UseTagsOptions): UseTagsReturn {
    const { collection_id, kind } = options;
    const { tags: tagsData } = useGlobalStorage();
    const error = writable<Error | null>(null);
    const isLoading = writable(false);

    const loadTags = () => {
        if (!collection_id) return;
        if (get(tagsData)[collection_id] !== undefined) return;

        const existingRequest = tagRequestsByCollection.get(collection_id);
        if (existingRequest) {
            isLoading.set(true);
            void existingRequest.finally(() => {
                isLoading.set(false);
            });
            return;
        }

        isLoading.set(true);
        const request = readTags({
            path: {
                collection_id
            }
        })
            .then((response) => {
                if (response.error) {
                    throw new Error(JSON.stringify(response.error));
                }
                if (response.data) {
                    // Store tags by collection_id to prevent preloading from overwriting other collections' tags
                    tagsData.update((tagsByCollection) => ({
                        ...tagsByCollection,
                        [collection_id]: response.data ?? []
                    }));
                }
            })
            .catch((err) => {
                error.set(err as Error);
            })
            .finally(() => {
                tagRequestsByCollection.delete(collection_id);
                isLoading.set(false);
            });

        tagRequestsByCollection.set(collection_id, request);
    };

    // Auto-load tags when hook is initialized
    if (collection_id && get(tagsData)[collection_id] === undefined) {
        loadTags();
    }

    const tags = derived(tagsData, ($tagsData) => {
        // Get tags for the current collection_id
        const allTags = $tagsData[collection_id] ?? [];
        if (!kind) return allTags;

        const _tags = allTags.filter((tag: Tag) => kind.includes(tag.kind));
        return _tags;
    });

    const tagsSelectedForCollection = derived(
        tagsSelectedByCollection,
        ($tagsSelectedByCollection) => {
            return $tagsSelectedByCollection[collection_id] ?? new Set<string>();
        }
    );

    const tagSelectionToggle = (tag_id: string) => {
        tagsSelectedByCollection.update((selectedByCollection) => {
            const selected = selectedByCollection[collection_id] ?? new Set<string>();
            if (selected.has(tag_id)) {
                selected.delete(tag_id);
            } else {
                selected.add(tag_id);
            }
            return {
                ...selectedByCollection,
                [collection_id]: new Set([...selected])
            };
        });
    };

    const clearTagsSelected = () => {
        tagsSelectedByCollection.update((selectedByCollection) => {
            return {
                ...selectedByCollection,
                [collection_id]: new Set()
            };
        });
    };

    return {
        tags: readonly(tags),
        loadTags,
        tagsSelected: readonly(tagsSelectedForCollection),
        tagSelectionToggle,
        clearTagsSelected,
        isLoading: readonly(isLoading),
        error
    };
}
