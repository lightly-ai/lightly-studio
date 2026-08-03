import { useQueryClient } from '@tanstack/svelte-query';
import type { InfiniteData } from '@tanstack/svelte-query';
import type { ImageView, ReadImagesResponse, TagByFilterBody } from '$lib/api/lightly_studio_local';
import { GRID_IMAGE_SEARCH_DROP_EVENT } from '$lib/components/GridItem';
import type { GridItemDragData } from '$lib/components/GridItem';
import { computeTagStates, resolveContextTargets } from '$lib/components/GridContextMenu';
import { useTagMutations } from '$lib/hooks';
import type { TagView } from '$lib/services/types';
import { getGridImageURL } from '$lib/utils';
import { get } from 'svelte/store';
import { patchSamplesTags } from './patchSamplesTags';

/** The subset of a grid sample the context menu needs. */
type ContextMenuSample = Pick<ImageView, 'sample_id' | 'file_name' | 'tags'>;

type SelectAllSnapshot = { filter: TagByFilterBody['filter']; size: number } | null;

interface UseImagesContextMenuParams {
    collectionId: string;
    /** Loaded grid samples in display order. */
    getSamples: () => ContextMenuSample[];
    getSelectedSampleIds: () => Set<string>;
    getAllTags: () => TagView[];
    getSelectAllSnapshot: () => SelectAllSnapshot;
    /** Query key of the images grid, so tag edits can be applied optimistically. */
    getSamplesQueryKey: () => readonly unknown[];
    onSamplesRefetch: () => void;
    onTagsRefetch: () => void;
    onOpenSample: (sampleId: string) => void;
}

const GRID_ITEM_SELECTOR = '[data-testid="sample-grid-item"]';

/**
 * Wires the grid context menu to the image grid: resolves the right-clicked target,
 * derives the tri-state tag checklist, and applies tag edits optimistically.
 *
 * @param params The collection, grid data getters, and refetch/navigation callbacks.
 * @returns Menu state plus the handlers `GridContextMenu` expects.
 */
export function useImagesContextMenu({
    collectionId,
    getSamples,
    getSelectedSampleIds,
    getAllTags,
    getSelectAllSnapshot,
    getSamplesQueryKey,
    onSamplesRefetch,
    onTagsRefetch,
    onOpenSample
}: UseImagesContextMenuParams) {
    const client = useQueryClient();

    let target = $state<{
        ids: string[];
        isSelectionTarget: boolean;
        clickedSampleId: string;
        clickedFileName: string;
    } | null>(null);

    const { busy, assignTag, assignByName, removeTag } = useTagMutations({
        collectionId,
        getTagKind: () => 'sample',
        getTargetIds: () => target?.ids ?? [],
        getSelectAllSnapshot,
        getExistingTags: getAllTags,
        onSamplesRefetch,
        onTagsRefetch
    });

    /** Tag ids per target we have loaded data for; unloaded targets are omitted. */
    const tagIdsPerKnownTarget = $derived.by(() => {
        if (!target) return [];
        const tagsBySampleId = new Map(
            getSamples().map((sample) => [sample.sample_id, sample.tags.map((tag) => tag.tag_id)])
        );
        return target.ids
            .map((id) => tagsBySampleId.get(id))
            .filter((tagIds): tagIds is string[] => tagIds !== undefined);
    });

    const tagStates = $derived(
        computeTagStates({
            tagIdsPerKnownTarget,
            allTagIds: getAllTags().map((tag) => tag.tag_id)
        })
    );

    const knownTargetNote = $derived.by(() => {
        const total = target?.ids.length ?? 0;
        const known = tagIdsPerKnownTarget.length;
        if (total === 0 || known === total) return undefined;
        return `Tag state shown for ${known} of ${total} loaded samples`;
    });

    const headerLabel = $derived.by(() => {
        if (!target) return '';
        return target.isSelectionTarget && target.ids.length > 1
            ? `${target.ids.length} samples`
            : target.clickedFileName;
    });

    const isSelectionTarget = $derived(target?.isSelectionTarget ?? false);

    function resolveTarget(event: MouseEvent): boolean {
        const tile = (event.target as HTMLElement | null)?.closest?.(GRID_ITEM_SELECTOR);
        const index = Number((tile as HTMLElement | null)?.dataset?.index);
        const sample = Number.isInteger(index) ? getSamples()[index] : undefined;
        if (!sample) {
            target = null;
            return false;
        }

        const { ids, isSelectionTarget: fromSelection } = resolveContextTargets({
            clickedId: sample.sample_id,
            selectedSampleIds: getSelectedSampleIds()
        });
        target = {
            ids,
            isSelectionTarget: fromSelection,
            clickedSampleId: sample.sample_id,
            clickedFileName: sample.file_name
        };
        return true;
    }

    // Patch the cached pages so the checklist reflects the click before the request
    // settles; onSamplesRefetch reconciles with the server afterwards.
    function patchCachedTags(tagId: string, action: 'add' | 'remove') {
        const tag = getAllTags().find((candidate) => candidate.tag_id === tagId);
        const sampleIds = target?.ids;
        if (!tag || !sampleIds?.length) return;

        client.setQueriesData<InfiniteData<ReadImagesResponse>>(
            { queryKey: getSamplesQueryKey() },
            (data) => patchSamplesTags(data, { sampleIds, tag, action })
        );
    }

    function toggleTag(tagId: string) {
        if (get(busy)) return;
        const isChecked = tagStates[tagId] === 'checked';
        patchCachedTags(tagId, isChecked ? 'remove' : 'add');
        void (isChecked ? removeTag(tagId) : assignTag(tagId));
    }

    function createAndAssign(name: string) {
        void assignByName(name);
    }

    function openTarget() {
        if (target) onOpenSample(target.clickedSampleId);
    }

    function findSimilarTarget() {
        if (!target) return;
        window.dispatchEvent(
            new CustomEvent<GridItemDragData>(GRID_IMAGE_SEARCH_DROP_EVENT, {
                detail: {
                    url: getGridImageURL({ sampleId: target.clickedSampleId, quality: 'raw' }),
                    fileName: target.clickedFileName
                }
            })
        );
    }

    return {
        get headerLabel() {
            return headerLabel;
        },
        get tagStates() {
            return tagStates;
        },
        get knownTargetNote() {
            return knownTargetNote;
        },
        get isSelectionTarget() {
            return isSelectionTarget;
        },
        busy,
        resolveTarget,
        toggleTag,
        createAndAssign,
        openTarget,
        findSimilarTarget
    };
}
