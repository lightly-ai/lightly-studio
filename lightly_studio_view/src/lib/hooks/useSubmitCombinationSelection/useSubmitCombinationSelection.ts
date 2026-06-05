import { createSampling } from '$lib/api/lightly_studio_local/sdk.gen';
import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import { get, readonly, writable, type Readable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { TagView } from '$lib/services/types';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { computeStrategyMetadata } from './computeStrategyMetadata';
import { toApiStrategy } from './strategyApiMapping';

type SelectionError = { error: string };

interface UseSubmitCombinationSelectionParams {
    tags: Readable<TagView[]>;
    setTagSelected: (tagId: string, isSelected: boolean) => void;
    loadTags: () => Promise<void>;
    closeSelectionDialog: () => void;
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
    toast.success('Selection created successfully');
    await params.loadTags();
    const newTag = get(params.tags).find((tag) => tag.name === selectionResultTagName);
    if (newTag) params.setTagSelected(newTag.tag_id, true);
    params.closeSelectionDialog();
}

export function useSubmitCombinationSelection(params: UseSubmitCombinationSelectionParams) {
    const _isSubmitting = writable(false);
    const _loadingMessage = writable('');

    async function submit(submitParams: SubmitParams): Promise<boolean> {
        if (get(_isSubmitting)) return false;
        const {
            collectionId,
            isVideoCollection,
            instances,
            nSamplesToSelect,
            selectionResultTagName,
            selectionFilter
        } = submitParams;

        _isSubmitting.set(true);

        try {
            const metadataOk = await computeAllStrategiesMetadata(
                instances,
                collectionId,
                isVideoCollection,
                (message) => _loadingMessage.set(message)
            );
            if (!metadataOk) return false;

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
                toast.error(
                    (response.error as SelectionError).error ?? 'Failed to create selection'
                );
                return false;
            }

            await handleSelectionSuccess(selectionResultTagName, params);
            return true;
        } catch (error) {
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
