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

/**
 * Describes the evaluation matches grid that is currently mounted. The grid
 * publishes this so the shared selection (the same store the images/annotations
 * grids use, the selection pill, and the select-all control all read) and the
 * left-panel Tags menu can act on matches.
 *
 * Selection is stored under `selectionCollectionId` (the route's collection, which
 * is what the selection pill and select-all summary are keyed to) as composite
 * `"<gtSampleId>|<predSampleId>"` ids — one per match. A match's ground-truth and
 * prediction boxes live in separate annotation collections, so when a tag is
 * applied the composite id is split and each side is tagged in its own collection.
 */
export type MatchTaggingContext = {
    selectionCollectionId: string;
    gtCollectionId: string | null;
    predCollectionId: string | null;
};

const matchTaggingContext = writable<MatchTaggingContext | null>(null);
const matchSelectAllHandler = writable<(() => Promise<void>) | null>(null);

export function setMatchTaggingContext(context: MatchTaggingContext): void {
    matchTaggingContext.set(context);
}

export function clearMatchTaggingContext(): void {
    matchTaggingContext.set(null);
}

export const matchTaggingContextStore: Readable<MatchTaggingContext | null> =
    readonly(matchTaggingContext);

export function setMatchSelectAllHandler(handler: () => Promise<void>): void {
    matchSelectAllHandler.set(handler);
}

export function clearMatchSelectAllHandler(): void {
    matchSelectAllHandler.set(null);
}

/** Run the matches grid's registered select-all, if a matches grid is mounted. */
export async function runMatchSelectAll(): Promise<void> {
    await get(matchSelectAllHandler)?.();
}

/** Build a composite selection id from a match's annotation sample ids. */
export function matchSelectionId(
    gtSampleId: string | null | undefined,
    predSampleId: string | null | undefined
): string {
    return `${gtSampleId ?? ''}|${predSampleId ?? ''}`;
}

interface UseMatchAnnotationTagsReturn {
    isMatchMode: Readable<boolean>;
    options: Readable<TagView[]>;
    hasSelection: Readable<boolean>;
    busy: Readable<boolean>;
    reloadOptions: () => Promise<void>;
    assign: (rawName: string) => Promise<void>;
}

/**
 * Creates and applies annotation tags to the annotations behind the currently
 * selected evaluation matches, across the ground-truth and prediction collections.
 */
export function useMatchAnnotationTags(): UseMatchAnnotationTagsReturn {
    const { selectedSampleAnnotationCropIds } = useGlobalStorage();
    const _busy = writable(false);
    const _tagsByCollection = writable<Record<string, TagView[]>>({});

    const isMatchMode = derived(matchTaggingContext, ($context) => $context != null);

    const collectionIds = derived(matchTaggingContext, ($context) =>
        $context
            ? [$context.gtCollectionId, $context.predCollectionId].filter(
                  (id): id is string => id != null
              )
            : []
    );

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
        await Promise.all(
            get(collectionIds).map((collectionId) =>
                loadCollectionTags(collectionId).catch(() => [])
            )
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

    const selectedIds = derived(
        [matchTaggingContext, selectedSampleAnnotationCropIds],
        ([$context, $cropsByCollection]) =>
            $context
                ? ($cropsByCollection[$context.selectionCollectionId] ?? new Set<string>())
                : new Set<string>()
    );

    const hasSelection = derived(selectedIds, ($selectedIds) => $selectedIds.size > 0);

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
        const context = get(matchTaggingContext);
        if (!name || !context || get(_busy)) return;

        // Split each "<gtSampleId>|<predSampleId>" selection id back into its two
        // annotations and group the sample ids by the collection that owns them.
        const sampleIdsByCollection = new Map<string, Set<string>>();
        const addTo = (collectionId: string | null, sampleId: string) => {
            if (!collectionId || !sampleId) return;
            const set = sampleIdsByCollection.get(collectionId) ?? new Set<string>();
            set.add(sampleId);
            sampleIdsByCollection.set(collectionId, set);
        };
        for (const selectionId of get(selectedIds)) {
            const [gtSampleId, predSampleId] = selectionId.split('|');
            addTo(context.gtCollectionId, gtSampleId);
            addTo(context.predCollectionId, predSampleId);
        }
        if (sampleIdsByCollection.size === 0) return;

        _busy.set(true);
        let taggedCount = 0;
        try {
            for (const [collectionId, sampleIds] of sampleIdsByCollection) {
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
        isMatchMode,
        options,
        hasSelection,
        busy: readonly(_busy),
        reloadOptions,
        assign
    };
}
