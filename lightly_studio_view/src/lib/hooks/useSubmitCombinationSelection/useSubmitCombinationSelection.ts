import { createSampling } from '$lib/api/lightly_studio_local/sdk.gen';
import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import { get, readonly, writable, type Readable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { TagView } from '$lib/services/types';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { usePostHog } from '$lib/hooks';
import { getMetadataComputations } from './getMetadataComputations';
import { toApiStrategy } from './strategyApiMapping';

type SelectionError = { error: string };

interface UseSubmitCombinationSelectionParams {
    tags: Readable<TagView[]>;
    setTagSelected: (tagId: string, isSelected: boolean) => void;
    loadTags: () => Promise<void>;
    closeSelectionDialog: () => void;
    filteredSampleCount: Readable<number>;
}

interface SubmitParams {
    collectionId: string;
    isVideoCollection: boolean;
    instances: StrategyInstance[];
    nSamplesToSelect: number;
    selectionResultTagName: string;
    selectionFilter: SamplingRequest['filter'];
    preselectedTagId?: string;
}

async function handleSelectionSuccess(
    selectionResultTagName: string,
    params: UseSubmitCombinationSelectionParams
): Promise<void> {
    toast.success('Sampling created successfully');
    await params.loadTags();
    const newTag = get(params.tags).find((tag) => tag.name === selectionResultTagName);
    if (newTag) params.setTagSelected(newTag.tag_id, true);
    params.closeSelectionDialog();
}

export function useSubmitCombinationSelection(params: UseSubmitCombinationSelectionParams) {
    const { trackEvent } = usePostHog();
    const { filteredSampleCount } = params;
    const _isSubmitting = writable(false);
    const _loadingMessage = writable('');

    async function submit(submitParams: SubmitParams): Promise<boolean> {
        if (get(_isSubmitting)) return false;

        _isSubmitting.set(true);

        const {
            collectionId,
            isVideoCollection,
            instances,
            nSamplesToSelect,
            selectionResultTagName,
            selectionFilter,
            preselectedTagId
        } = submitParams;

        const filteredCount = get(filteredSampleCount);

        trackEvent('sampling_submitted', {
            collection_id: collectionId,
            strategies: instances.map((i) => i.type),
            n_samples: nSamplesToSelect,
            filtered_sample_count: filteredCount
        });

        try {
            if (isVideoCollection && instances.some((instance) => instance.type === 'similarity')) {
                toast.error('Similarity is only available for image collections.');
                return false;
            }

            _loadingMessage.set('Creating selection...');
            const response = await createSampling({
                path: { collection_id: collectionId },
                body: {
                    n_samples_to_select: nSamplesToSelect,
                    sampling_result_tag_name: selectionResultTagName,
                    strategies: instances.map(toApiStrategy),
                    metadata_computations: getMetadataComputations(instances),
                    filter: selectionFilter ?? undefined,
                    ...(preselectedTagId && { preselected_tag_id: preselectedTagId })
                }
            });

            if (response.error) {
                const errorMessage =
                    (response.error as SelectionError).error ?? 'Failed to create selection';
                trackEvent('sampling_triggered', {
                    collection_id: collectionId,
                    strategies: instances.map((i) => i.type),
                    n_samples: nSamplesToSelect,
                    filtered_sample_count: filteredCount,
                    success: false,
                    error_message: errorMessage
                });
                toast.error(errorMessage);
                return false;
            }

            trackEvent('sampling_triggered', {
                collection_id: collectionId,
                strategies: instances.map((i) => i.type),
                n_samples: nSamplesToSelect,
                filtered_sample_count: filteredCount,
                success: true,
                error_message: null
            });
            try {
                await handleSelectionSuccess(selectionResultTagName, params);
            } catch (uiError) {
                console.error('Unexpected error in handleSelectionSuccess:', uiError);
            }
            return true;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            trackEvent('sampling_triggered', {
                collection_id: collectionId,
                strategies: instances.map((i) => i.type),
                n_samples: nSamplesToSelect,
                filtered_sample_count: filteredCount,
                success: false,
                error_message: errorMessage
            });
            console.error('Unexpected error in useSubmitCombinationSelection.submit:', error);
            toast.error('Failed to create selection: ' + errorMessage);
            return false;
        } finally {
            _isSubmitting.set(false);
            _loadingMessage.set('');
        }
    }

    return {
        isSubmitting: readonly(_isSubmitting),
        loadingMessage: readonly(_loadingMessage),
        submit
    };
}
