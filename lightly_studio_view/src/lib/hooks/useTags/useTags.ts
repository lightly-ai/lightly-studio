import type { TagView as Tag, TagKind } from '$lib/services/types';
import { isReadableStore } from '$lib/hooks/utils/isReadableStore';
import { derived, get, readonly, readable, writable, type Readable } from 'svelte/store';
import { readTags } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '../useGlobalStorage';

interface UseTagsOptions {
    collection_id: string | Readable<string>;
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
    const error = writable<Error | null>(null);
    const isLoading = writable(false);
    const loadedCollectionIds = new Set<string>();
    const pendingCollectionIds = new Set<string>();

    const collectionIdStore = isReadableStore<string>(collection_id)
        ? collection_id
        : readable(collection_id);

    const loadTagsForCollection = (currentCollectionId: string, force = false) => {
        if (!currentCollectionId) return;
        if (!force && loadedCollectionIds.has(currentCollectionId)) return;
        if (pendingCollectionIds.has(currentCollectionId)) return;

        pendingCollectionIds.add(currentCollectionId);
        isLoading.set(true);
        error.set(null);

        readTags({
            path: {
                collection_id: currentCollectionId
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
                        [currentCollectionId]: response.data ?? []
                    }));
                }
                loadedCollectionIds.add(currentCollectionId);
            })
            .catch((err: unknown) => {
                error.set(err instanceof Error ? err : new Error(String(err)));
            })
            .finally(() => {
                pendingCollectionIds.delete(currentCollectionId);
                isLoading.set(pendingCollectionIds.size > 0);
            });
    };

    const loadTags = () => {
        loadTagsForCollection(get(collectionIdStore), true);
    };

    loadTagsForCollection(get(collectionIdStore));

    const tags = derived([tagsData, collectionIdStore], ([$tagsData, $collectionId]) => {
        loadTagsForCollection($collectionId);

        // Get tags for the current collection_id
        const allTags = $collectionId ? ($tagsData[$collectionId] ?? []) : [];
        if (!kind) return allTags;

        const _tags = allTags.filter((tag: Tag) => kind.includes(tag.kind));
        return _tags;
    });

    const tagsSelectedForCollection = derived(
        [tagsSelectedByCollection, collectionIdStore],
        ([$tagsSelectedByCollection, $collectionId]) => {
            loadTagsForCollection($collectionId);

            if (!$collectionId) {
                return new Set<string>();
            }

            return $tagsSelectedByCollection[$collectionId] ?? new Set<string>();
        }
    );

    const tagSelectionToggle = (tag_id: string) => {
        const currentCollectionId = get(collectionIdStore);
        if (!currentCollectionId) {
            return;
        }

        tagsSelectedByCollection.update((selectedByCollection) => {
            const selected = selectedByCollection[currentCollectionId] ?? new Set<string>();
            if (selected.has(tag_id)) {
                selected.delete(tag_id);
            } else {
                selected.add(tag_id);
            }
            return {
                ...selectedByCollection,
                [currentCollectionId]: new Set([...selected])
            };
        });
    };

    const clearTagsSelected = () => {
        const currentCollectionId = get(collectionIdStore);
        if (!currentCollectionId) {
            return;
        }

        tagsSelectedByCollection.update((selectedByCollection) => {
            return {
                ...selectedByCollection,
                [currentCollectionId]: new Set()
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
