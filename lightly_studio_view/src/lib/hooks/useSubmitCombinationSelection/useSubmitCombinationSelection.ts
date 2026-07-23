import { createSampling } from '$lib/api/lightly_studio_local/sdk.gen';
import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import { get, readonly, writable, type Readable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { TagView } from '$lib/services/types';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { usePostHog } from '$lib/hooks';
import { computeStrategyMetadata } from './computeStrategyMetadata';
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
}

async function computeAllStrategiesMetadata(
    instances: StrategyInstance[],
    collectionId: string,
    isVideoCollection: boolean,
    onProgress: (message: string) => void
): Promise<boolean> {
    for (const instance of instances) {
        const ok = await computeStrategyMetadata({
            instance,
            collectionId,
            isVideoCollection,
            onProgress
        });
        if (!ok) return false;
    }
    return true;
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
            selectionFilter
        } = submitParams;

        const filteredCount = get(filteredSampleCount);

        trackEvent('sampling_submitted', {
            collection_id: collectionId,
            strategies: instances.map((i) => i.type),
            n_samples: nSamplesToSelect,
            filtered_sample_count: filteredCount
        });

        try {
            const metadataOk = await computeAllStrategiesMetadata(
                instances,
                collectionId,
                isVideoCollection,
                (message) => _loadingMessage.set(message)
            );
            if (!metadataOk) {
                trackEvent('sampling_triggered', {
                    collection_id: collectionId,
                    strategies: instances.map((i) => i.type),
                    n_samples: nSamplesToSelect,
                    filtered_sample_count: filteredCount,
                    success: false,
                    error_message: 'Metadata computation failed'
                });
                return false;
            }

            _loadingMessage.set('Creating selection...');
            const response = await createSampling({
                path: { collection_id: collectionId },
                body: {
                    n_samples_to_select: nSamplesToSelect,
                    sampling_result_tag_name: selectionResultTagName,
                    strategies: instances.map(toApiStrategy),
                    filter: selectionFilter ?? undefined
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
            await handleSelectionSuccess(selectionResultTagName, params);
            return true;
        } catch (error) {
            trackEvent('sampling_triggered', {
                collection_id: collectionId,
                strategies: instances.map((i) => i.type),
                n_samples: nSamplesToSelect,
                filtered_sample_count: filteredCount,
                success: false,
                error_message: (error as Error).message
            });
            console.error('Unexpected error in useSubmitCombinationSelection.submit:', error);
            toast.error('Failed to create selection: ' + (error as Error).message);
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
