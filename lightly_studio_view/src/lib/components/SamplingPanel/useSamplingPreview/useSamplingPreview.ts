import { get, readonly, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import {
    addSampleIdsToTagId,
    createTag,
    previewSampling
} from '$lib/api/lightly_studio_local/sdk.gen';
import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import { getErrorMessage } from '$lib/api/ApiError';
import { useImageFilters } from '$lib/hooks';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { getMetadataComputations } from '$lib/hooks/useSubmitCombinationSelection/getMetadataComputations';
import { toApiStrategy } from '$lib/hooks/useSubmitCombinationSelection/strategyApiMapping';

interface RunPreviewParams {
    collectionId: string;
    instances: StrategyInstance[];
    nSamplesToSelect: number;
}

/**
 * Runs a sampling as a draft and shows the picked samples in the grid.
 *
 * The filter that was active when the draft started is the sampling input, so a second
 * preview samples from the same candidates rather than from the first draft.
 */
export function useSamplingPreview() {
    const { filterParams, imageFilter, updateSampleIds } = useImageFilters();

    const draftSampleIds = writable<string[] | null>(null);
    const isRunning = writable(false);
    const isKeeping = writable(false);

    let inputFilter: SamplingRequest['filter'] = undefined;
    type FilterParams = Parameters<typeof filterParams.set>[0];
    let filterParamsBeforeDraft: FilterParams | null = null;

    async function runPreview(params: RunPreviewParams): Promise<void> {
        if (get(isRunning)) return;
        isRunning.set(true);
        try {
            if (filterParamsBeforeDraft === null) {
                filterParamsBeforeDraft = get(filterParams);
                inputFilter = get(imageFilter) as SamplingRequest['filter'];
            }
            const response = await previewSampling({
                path: { collection_id: params.collectionId },
                body: {
                    n_samples_to_select: params.nSamplesToSelect,
                    strategies: params.instances.map(toApiStrategy),
                    metadata_computations: getMetadataComputations(params.instances),
                    filter: inputFilter ?? undefined
                }
            });
            if (response.error || !response.data) {
                toast.error(getErrorMessage(response.error, 'Failed to preview the sampling'));
                return;
            }
            draftSampleIds.set(response.data.sample_ids);
            updateSampleIds(response.data.sample_ids);
        } finally {
            isRunning.set(false);
        }
    }

    async function keepAsTag(
        collectionId: string,
        tagName: string,
        onKept: (tagId: string) => Promise<void>
    ): Promise<boolean> {
        const sampleIds = get(draftSampleIds);
        if (!sampleIds || get(isKeeping)) return false;
        isKeeping.set(true);
        try {
            const tag = await createTag({
                path: { collection_id: collectionId },
                body: { name: tagName }
            });
            if (tag.error || !tag.data) {
                toast.error(getErrorMessage(tag.error, 'Failed to create the tag'));
                return false;
            }
            const added = await addSampleIdsToTagId({
                path: { collection_id: collectionId, tag_id: tag.data.tag_id },
                body: { sample_ids: sampleIds }
            });
            if (added.error) {
                toast.error(getErrorMessage(added.error, 'Failed to add the samples to the tag'));
                return false;
            }
            toast.success(`Kept ${sampleIds.length} samples as "${tagName}"`);
            endDraft();
            await onKept(tag.data.tag_id);
            return true;
        } finally {
            isKeeping.set(false);
        }
    }

    function discardDraft(): void {
        endDraft();
    }

    /** Puts the grid back to the filter the draft started from. */
    function endDraft(): void {
        if (filterParamsBeforeDraft !== null) {
            filterParams.set(filterParamsBeforeDraft);
        }
        draftSampleIds.set(null);
        filterParamsBeforeDraft = null;
        inputFilter = undefined;
    }

    return {
        draftSampleIds: readonly(draftSampleIds),
        isRunning: readonly(isRunning),
        isKeeping: readonly(isKeeping),
        runPreview,
        keepAsTag,
        discardDraft
    };
}
