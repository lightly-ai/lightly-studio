import {
    addSampleIdsToTagId,
    createTag,
    readTags,
    type TagView
} from '$lib/api/lightly_studio_local';
import { derived, get, readonly, writable, type Readable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { useGlobalStorage } from '../useGlobalStorage';

const ANNOTATION_KIND = 'annotation' as const;

// The annotation collections (ground truth + prediction) currently shown in the
// evaluation matches grid. The grid publishes them here so the left-panel Tags
// menu knows which collections a tag must be created in and applied to. A match's
// ground-truth and prediction boxes live in separate annotation collections, so a
// single tag name is created (find-or-create) once per collection.
const matchTaggingCollectionIds = writable<string[]>([]);

export function setMatchTaggingCollectionIds(ids: string[]): void {
    matchTaggingCollectionIds.set(ids);
}

export function clearMatchTaggingCollectionIds(): void {
    matchTaggingCollectionIds.set([]);
}

export const matchTaggingCollectionIdsStore: Readable<string[]> =
    readonly(matchTaggingCollectionIds);

interface UseMatchAnnotationTagsReturn {
    options: Readable<TagView[]>;
    hasSelection: Readable<boolean>;
    busy: Readable<boolean>;
    reloadOptions: () => Promise<void>;
    assign: (rawName: string) => Promise<void>;
}

/**
 * Adds annotation tags to the annotations behind the currently selected evaluation
 * matches. Selection is read from the shared annotation-crop selection store, where
 * each selected annotation is grouped by the (ground-truth or prediction) collection
 * that owns it, so a true positive's two boxes are tagged in their two collections.
 */
export function useMatchAnnotationTags(): UseMatchAnnotationTagsReturn {
    const { selectedSampleAnnotationCropIds } = useGlobalStorage();
    const _busy = writable(false);
    const _tagsByCollection = writable<Record<string, TagView[]>>({});

    async function loadCollectionTags(collectionId: string): Promise<TagView[]> {
        const response = await readTags({ path: { collection_id: collectionId } });
        if (response.error || !response.data) {
            throw new Error('failed to load tags');
        }
        const annotationTags = response.data.filter((tag) => tag.kind === ANNOTATION_KIND);
        _tagsByCollection.update((byCollection) => ({
            ...byCollection,
            [collectionId]: annotationTags
        }));
        return annotationTags;
    }

    async function reloadOptions(): Promise<void> {
        const collectionIds = get(matchTaggingCollectionIds);
        await Promise.all(
            collectionIds.map((collectionId) => loadCollectionTags(collectionId).catch(() => []))
        );
    }

    // Deduplicate by name so the picker shows each tag once even when the
    // ground-truth and prediction collections both already have it.
    const options: Readable<TagView[]> = derived(_tagsByCollection, ($tagsByCollection) => {
        const byName = new Map<string, TagView>();
        for (const tags of Object.values($tagsByCollection)) {
            for (const tag of tags) {
                if (!byName.has(tag.name)) byName.set(tag.name, tag);
            }
        }
        return Array.from(byName.values());
    });

    // Selected annotation ids grouped by the collection that owns them, restricted
    // to the collections of the current matches view.
    const selectedByCollection = derived(
        [matchTaggingCollectionIds, selectedSampleAnnotationCropIds],
        ([$collectionIds, $cropsByCollection]) => {
            const grouped = new Map<string, Set<string>>();
            for (const collectionId of $collectionIds) {
                const crops = $cropsByCollection[collectionId];
                if (crops && crops.size > 0) {
                    grouped.set(collectionId, crops);
                }
            }
            return grouped;
        }
    );

    const hasSelection = derived(selectedByCollection, ($grouped) => $grouped.size > 0);

    async function ensureTagId(collectionId: string, name: string): Promise<string> {
        const cached =
            get(_tagsByCollection)[collectionId] ?? (await loadCollectionTags(collectionId));
        const existing = cached.find((tag) => tag.name === name);
        if (existing) return existing.tag_id;

        const response = await createTag({
            path: { collection_id: collectionId },
            body: { name, kind: ANNOTATION_KIND }
        });
        const created = response.data;
        if (response.error || !created?.tag_id) {
            throw new Error('failed to create tag');
        }
        _tagsByCollection.update((byCollection) => ({
            ...byCollection,
            [collectionId]: [...(byCollection[collectionId] ?? []), created]
        }));
        return created.tag_id;
    }

    async function assign(rawName: string): Promise<void> {
        const name = rawName.trim();
        if (!name || get(_busy)) return;

        const groups = get(selectedByCollection);
        if (groups.size === 0) return;

        _busy.set(true);
        let taggedCount = 0;
        try {
            for (const [collectionId, sampleIds] of groups) {
                const tagId = await ensureTagId(collectionId, name);
                const response = await addSampleIdsToTagId({
                    path: { collection_id: collectionId, tag_id: tagId },
                    body: { sample_ids: [...sampleIds] }
                });
                if (response.error) throw new Error('failed to add tag');
                taggedCount += sampleIds.size;
            }
        } catch {
            toast.error('Failed to add tag. Please try again.');
            return;
        } finally {
            _busy.set(false);
        }
        toast.success(
            `Tagged ${taggedCount} annotation${taggedCount === 1 ? '' : 's'} with "${name}"`
        );
        void reloadOptions();
    }

    return {
        options,
        hasSelection,
        busy: readonly(_busy),
        reloadOptions,
        assign
    };
}
