import type { TagView as Tag } from '$lib/services/types';
import { derived, get, readonly, writable, type Readable } from 'svelte/store';
import { readTags } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '../useGlobalStorage';
import { usePostHog } from '$lib/hooks';
import { toggleTagSelection } from './toggleTagSelection';

interface UseTagsOptions {
    collection_id: string;
    /** Whether to load the tags of the collection when the hook is created. */
    autoLoad?: boolean;
}

interface UseTagsReturn {
    tags: Readable<Tag[]>;
    tagsSelected: Readable<Set<string>>;
    clearTagsSelected: () => void;
    clearTagSelected: (tagId: string) => void;
    setTagSelected: (tagId: string, isSelected: boolean) => void;
    /** Replaces the whole tag selection of the collection in one update and tracks each change. */
    setTagsSelected: (tagIds: string[]) => void;
    loadTags: () => Promise<void>;
    tagSelectionToggle: (tagId: string) => void;
    isLoading: Readable<boolean>;
    error: Readable<Error | null>;
}

/** The maximum page size of the tags endpoint. */
const TAGS_PAGE_SIZE = 100;

const tagsSelectedByCollection = writable<Record<string, Set<string>>>({});

export function useTags(options: UseTagsOptions): UseTagsReturn {
    const { collection_id, autoLoad = true } = options;
    const { tags: tagsData } = useGlobalStorage();
    const { trackEvent } = usePostHog();
    const isLoaded = writable(false);
    const error = writable<Error | null>(null);
    const isLoading = writable(false);
    let currentLoadPromise: Promise<void> | null = null;

    const loadTags = async () => {
        if (get(isLoading)) return currentLoadPromise ?? Promise.resolve();
        if (!collection_id) return;

        isLoading.set(true);
        currentLoadPromise = readAllTags(collection_id)
            .then((allTags) => {
                const validTagIds = allTags.map((tag) => tag.tag_id);

                // Store tags by collection_id to prevent preloading from overwriting other collections' tags
                tagsData.update((tagsByCollection) => ({
                    ...tagsByCollection,
                    [collection_id]: allTags
                }));

                tagsSelectedByCollection.update((selectedByCollection) => {
                    const selected = selectedByCollection[collection_id] ?? new Set<string>();
                    const prunedSelected = new Set(
                        Array.from(selected).filter((tagId) => validTagIds.includes(tagId))
                    );

                    return {
                        ...selectedByCollection,
                        [collection_id]: prunedSelected
                    };
                });
            })
            .catch((err) => {
                error.set(err as Error);
            })
            .finally(() => {
                isLoading.set(false);
                currentLoadPromise = null;
            });

        return currentLoadPromise;
    };

    // Auto-load tags when hook is initialized
    if (autoLoad && !get(isLoaded) && collection_id) {
        void loadTags();
        isLoaded.set(true);
    }

    const tags = derived(tagsData, ($tagsData) => $tagsData[collection_id] ?? []);

    const tagsSelectedForCollection = derived(
        tagsSelectedByCollection,
        ($tagsSelectedByCollection) => {
            return $tagsSelectedByCollection[collection_id] ?? new Set<string>();
        }
    );

    const tagSelectionToggle = (tag_id: string) => {
        toggleTagSelection({
            tagId: tag_id,
            collectionId: collection_id,
            currentSelected: get(tagsSelectedByCollection)[collection_id] ?? new Set<string>(),
            allTags: get(tagsData)[collection_id] ?? [],
            updateSelected: (collectionId, newSelected) => {
                tagsSelectedByCollection.update((selectedByCollection) => ({
                    ...selectedByCollection,
                    [collectionId]: newSelected
                }));
            },
            trackEvent
        });
    };

    const replaceTagsSelected = (tagIds: Iterable<string>) => {
        tagsSelectedByCollection.update((selectedByCollection) => ({
            ...selectedByCollection,
            [collection_id]: new Set(tagIds)
        }));
    };

    const clearTagsSelected = () => replaceTagsSelected([]);

    const clearTagSelected = (tagId: string) => {
        tagsSelectedByCollection.update((selectedByCollection) => {
            const selected = new Set(selectedByCollection[collection_id] ?? []);
            selected.delete(tagId);

            return {
                ...selectedByCollection,
                [collection_id]: selected
            };
        });
    };

    const setTagSelected = (tagId: string, isSelected: boolean) => {
        tagsSelectedByCollection.update((selectedByCollection) => {
            const selected = new Set(selectedByCollection[collection_id] ?? []);
            if (isSelected) {
                selected.add(tagId);
            } else {
                selected.delete(tagId);
            }
            return {
                ...selectedByCollection,
                [collection_id]: selected
            };
        });
    };

    const setTagsSelected = (tagIds: string[]) => {
        const previous = get(tagsSelectedByCollection)[collection_id] ?? new Set<string>();
        const next = new Set(tagIds);
        replaceTagsSelected(next);

        const tagNames = new Map(
            (get(tagsData)[collection_id] ?? []).map((tag) => [tag.tag_id, tag.name])
        );
        const track = (tagId: string, action: 'selected' | 'unselected') =>
            trackEvent('grid_filter_toggled', {
                collection_id,
                filter_type: 'tag',
                filter_value: tagNames.get(tagId) ?? tagId,
                action,
                active_count: next.size
            });
        next.forEach((tagId) => !previous.has(tagId) && track(tagId, 'selected'));
        previous.forEach((tagId) => !next.has(tagId) && track(tagId, 'unselected'));
    };

    return {
        tags: readonly(tags),
        loadTags,
        tagsSelected: readonly(tagsSelectedForCollection),
        tagSelectionToggle,
        setTagSelected,
        setTagsSelected,
        clearTagsSelected,
        clearTagSelected,
        isLoading: readonly(isLoading),
        error
    };
}

/** Reads every tag of the collection. The endpoint returns at most `TAGS_PAGE_SIZE` tags per request. */
async function readAllTags(collectionId: string): Promise<Tag[]> {
    const allTags: Tag[] = [];
    for (let offset = 0; ; offset += TAGS_PAGE_SIZE) {
        const response = await readTags({
            path: { collection_id: collectionId },
            query: { offset, limit: TAGS_PAGE_SIZE }
        });
        if (response.error) throw response.error;
        const page = response.data ?? [];
        allTags.push(...page);
        if (page.length < TAGS_PAGE_SIZE) return allTags;
    }
}
