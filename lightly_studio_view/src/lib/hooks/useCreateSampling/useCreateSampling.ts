import {
    createSampling,
    computeSimilarityMetadata,
    computeTypicalityMetadata
} from '$lib/api/lightly_studio_local/sdk.gen';
import { get, readonly, writable, type Readable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { TagView } from '$lib/services/types';
import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import type { BalancingMode } from '$lib/components/Sampling/balancingMode';

type SamplingError = { error: string };

function extractError(error: unknown, fallback: string): string {
    return (error as SamplingError)?.error || fallback;
}

interface UseCreateSamplingParams {
    tags: Readable<TagView[]>;
    setTagSelected: (tagId: string, isSelected: boolean) => void;
    loadTags: () => Promise<void>;
    closeSamplingDialog: () => void;
}

interface SubmitParams {
    collectionId: string;
    isSimilaritySupported: boolean;
    samplingStrategy: 'diversity' | 'typicality' | 'similarity' | 'class_balancing';
    nSamplesToSelect: number;
    samplingResultTagName: string;
    queryTagId: string;
    balancingMode: BalancingMode;
    samplingFilter: SamplingRequest['filter'];
}

export function useCreateSampling(params: UseCreateSamplingParams) {
    const _isSubmitting = writable(false);
    const _loadingMessage = writable('');

    async function performSampling(
        collectionId: string,
        strategies: SamplingRequest['strategies'],
        samplingFilter: SamplingRequest['filter'],
        n: number,
        tagName: string
    ): Promise<boolean> {
        _loadingMessage.set('Creating sampling...');
        const response = await createSampling({
            path: { collection_id: collectionId },
            body: {
                n_samples_to_select: n,
                sampling_result_tag_name: tagName,
                strategies,
                filter: samplingFilter ?? undefined
            }
        });

        if (response.error) {
            toast.error(extractError(response.error, 'Failed to create sampling'));
            return false;
        }

        toast.success('Sampling created successfully');
        await params.loadTags();
        const newTag = get(params.tags).find((tag) => tag.name === tagName);
        if (newTag) params.setTagSelected(newTag.tag_id, true);
        params.closeSamplingDialog();
        return true;
    }

    async function submit(submitParams: SubmitParams): Promise<boolean | undefined> {
        if (get(_isSubmitting)) return;
        const {
            collectionId,
            isSimilaritySupported,
            samplingStrategy,
            nSamplesToSelect,
            samplingResultTagName,
            queryTagId,
            balancingMode,
            samplingFilter
        } = submitParams;
        _isSubmitting.set(true);

        try {
            if (samplingStrategy === 'class_balancing') {
                return await performSampling(
                    collectionId,
                    [{ strategy_name: 'balance', target_distribution: balancingMode }],
                    samplingFilter,
                    nSamplesToSelect,
                    samplingResultTagName
                );
            }

            if (samplingStrategy === 'diversity') {
                return await performSampling(
                    collectionId,
                    [{ strategy_name: 'diversity', embedding_model_name: null }],
                    samplingFilter,
                    nSamplesToSelect,
                    samplingResultTagName
                );
            }

            if (samplingStrategy === 'typicality') {
                _loadingMessage.set('Computing typicality metadata...');
                const typicalityResponse = await computeTypicalityMetadata({
                    path: { collection_id: collectionId },
                    body: { embedding_model_name: null, metadata_name: 'typicality' }
                });

                if (typicalityResponse.error) {
                    toast.error(
                        'Failed to compute typicality metadata: ' +
                            extractError(typicalityResponse.error, 'Unknown error')
                    );
                    return false;
                }

                return await performSampling(
                    collectionId,
                    [{ strategy_name: 'weights', metadata_key: 'typicality' }],
                    samplingFilter,
                    nSamplesToSelect,
                    samplingResultTagName
                );
            }

            if (samplingStrategy === 'similarity') {
                if (!isSimilaritySupported) {
                    toast.error('Similarity is only available for image collections.');
                    return false;
                }

                _loadingMessage.set('Computing similarity metadata...');
                const simResponse = await computeSimilarityMetadata({
                    path: { collection_id: collectionId, query_tag_id: queryTagId },
                    body: { embedding_model_name: null, metadata_name: 'similarity' }
                });

                if (simResponse.error) {
                    toast.error(
                        'Failed to compute similarity metadata: ' +
                            extractError(simResponse.error, 'Unknown error')
                    );
                    return false;
                }

                return await performSampling(
                    collectionId,
                    [{ strategy_name: 'weights', metadata_key: 'similarity' }],
                    samplingFilter,
                    nSamplesToSelect,
                    samplingResultTagName
                );
            }

            return false;
        } catch (error) {
            // API functions return { data, error } and don't throw, so this
            // only fires for unexpected runtime bugs in the hook itself.
            console.error('Unexpected error in useCreateSampling.submit:', error);
            toast.error('Failed to create sampling: ' + (error as Error).message);
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
