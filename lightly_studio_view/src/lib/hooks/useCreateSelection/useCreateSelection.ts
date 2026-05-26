import {
    createCombinationSelection,
    computeSimilarityMetadata,
    computeTypicalityMetadata
} from '$lib/api/lightly_studio_local/sdk.gen';
import { get, readonly, writable, type Readable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { TagView } from '$lib/services/types';
import type { SelectionRequest } from '$lib/api/lightly_studio_local/types.gen';
import type { BalancingMode } from '$lib/components/Selection/balancingMode';

type SelectionError = { error: string };

function extractError(error: unknown, fallback: string): string {
    return (error as SelectionError)?.error || fallback;
}

interface UseCreateSelectionParams {
    collectionId: string;
    isSimilaritySupported: boolean;
    tags: Readable<TagView[]>;
    setTagSelected: (tagId: string, isSelected: boolean) => void;
    loadTags: () => Promise<void>;
    closeSelectionDialog: () => void;
}

interface SubmitParams {
    selectionStrategy: 'diversity' | 'typicality' | 'similarity' | 'class_balancing';
    nSamplesToSelect: number;
    selectionResultTagName: string;
    queryTagId: string;
    balancingMode: BalancingMode;
    selectionFilter: SelectionRequest['filter'];
}

export function useCreateSelection(params: UseCreateSelectionParams) {
    const {
        collectionId,
        isSimilaritySupported,
        tags,
        setTagSelected,
        loadTags,
        closeSelectionDialog
    } = params;
    const _isSubmitting = writable(false);
    const _loadingMessage = writable('');

    async function performSelection(
        strategies: SelectionRequest['strategies'],
        selectionFilter: SelectionRequest['filter'],
        n: number,
        tagName: string
    ): Promise<boolean> {
        _loadingMessage.set('Creating selection...');
        const response = await createCombinationSelection({
            path: { collection_id: collectionId },
            body: {
                n_samples_to_select: n,
                selection_result_tag_name: tagName,
                strategies,
                filter: selectionFilter ?? undefined
            }
        });

        if (response.error) {
            toast.error(extractError(response.error, 'Failed to create selection'));
            return false;
        }

        toast.success('Selection created successfully');
        await loadTags();
        const newTag = get(tags).find((tag) => tag.name === tagName);
        if (newTag) setTagSelected(newTag.tag_id, true);
        closeSelectionDialog();
        return true;
    }

    async function submit(submitParams: SubmitParams): Promise<boolean | undefined> {
        if (get(_isSubmitting)) return;
        const {
            selectionStrategy,
            nSamplesToSelect,
            selectionResultTagName,
            queryTagId,
            balancingMode,
            selectionFilter
        } = submitParams;
        _isSubmitting.set(true);

        try {
            if (selectionStrategy === 'class_balancing') {
                return await performSelection(
                    [{ strategy_name: 'balance', target_distribution: balancingMode }],
                    selectionFilter,
                    nSamplesToSelect,
                    selectionResultTagName
                );
            }

            if (selectionStrategy === 'diversity') {
                return await performSelection(
                    [{ strategy_name: 'diversity', embedding_model_name: null }],
                    selectionFilter,
                    nSamplesToSelect,
                    selectionResultTagName
                );
            }

            if (selectionStrategy === 'typicality') {
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

                return await performSelection(
                    [{ strategy_name: 'weights', metadata_key: 'typicality' }],
                    selectionFilter,
                    nSamplesToSelect,
                    selectionResultTagName
                );
            }

            if (selectionStrategy === 'similarity') {
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

                return await performSelection(
                    [{ strategy_name: 'weights', metadata_key: 'similarity' }],
                    selectionFilter,
                    nSamplesToSelect,
                    selectionResultTagName
                );
            }

            return false;
        } catch (error) {
            // API functions return { data, error } and don't throw, so this
            // only fires for unexpected runtime bugs in the hook itself.
            console.error('Unexpected error in useCreateSelection.submit:', error);
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
