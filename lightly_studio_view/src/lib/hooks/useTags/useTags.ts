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

export function useTags(options: UseTagsOptions): UseTagsReturn {
    const { collection_id, kind } = options;
    const { tags: tagsData } = useGlobalStorage();
    const isLoaded = writable(false);
    const error = writable<Error | null>(null);
    const isLoading = writable(false);

    const loadTags = () => {
        if (get(isLoading)) return;
        if (!collection_id) return;

        isLoading.set(true);
        readTags({
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
                isLoading.set(false);
            });
    };

    // Auto-load tags when hook is initialized
    if (!get(isLoaded) && collection_id) {
        loadTags();
        isLoaded.set(true);
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
