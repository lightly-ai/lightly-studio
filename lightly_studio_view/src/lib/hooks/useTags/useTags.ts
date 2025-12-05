import type { TagView as Tag, TagKind } from '$lib/services/types';
import { derived, get, readonly, writable, type Readable } from 'svelte/store';
import { readTags } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '../useGlobalStorage';

interface UseTagsOptions {
    dataset_id: string;
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

const tagsSelectedByDataset = writable<Record<string, Set<string>>>({});

export function useTags(options: UseTagsOptions): UseTagsReturn {
    const { dataset_id, kind } = options;
    const { tags: tagsData } = useGlobalStorage();
    const isLoaded = writable(false);
    const error = writable<Error | null>(null);
    const isLoading = writable(false);

    const loadTags = () => {
        if (get(isLoading)) return;

        isLoading.set(true);
        readTags({
            path: {
                dataset_id
            }
        })
            .then((response) => {
                if (response.error) {
                    throw new Error(JSON.stringify(response.error));
                }
                if (response.data) {
                    tagsData.set(response.data);
                }
            })
            .catch((err) => {
                error.set(err as Error);
            })
            .finally(() => {
                isLoading.set(false);
            });
    };

    // const tags = writable([] as Tag[]);
    if (!get(isLoaded) && dataset_id) {
        loadTags();
        isLoaded.set(true);
    }

    const tags = derived(tagsData, ($tagsData) => {
        const allTags = $tagsData ?? [];
        if (!kind) return allTags;

        const _tags = allTags.filter((tag: Tag) => kind.includes(tag.kind));
        return _tags;
    });

    const tagsSelectedForDataset = derived(tagsSelectedByDataset, ($tagsSelectedByDataset) => {
        return $tagsSelectedByDataset[dataset_id] ?? new Set<string>();
    });

    const tagSelectionToggle = (tag_id: string) => {
        tagsSelectedByDataset.update((selectedByDataset) => {
            const selected = selectedByDataset[dataset_id] ?? new Set<string>();
            if (selected.has(tag_id)) {
                selected.delete(tag_id);
            } else {
                selected.add(tag_id);
            }
            return {
                ...selectedByDataset,
                [dataset_id]: new Set([...selected])
            };
        });
    };

    const clearTagsSelected = () => {
        tagsSelectedByDataset.update((selectedByDataset) => {
            return {
                ...selectedByDataset,
                [dataset_id]: new Set()
            };
        });
    };

    return {
        tags: readonly(tags),
        loadTags,
        tagsSelected: readonly(tagsSelectedForDataset),
        tagSelectionToggle,
        clearTagsSelected,
        isLoading: readonly(isLoading),
        error
    };
}
