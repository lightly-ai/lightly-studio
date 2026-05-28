import {
    createSampling,
    computeSimilarityMetadata,
    computeTypicalityMetadata
} from '$lib/api/lightly_studio_local/sdk.gen';
import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCreateSelection } from './useCreateSelection';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    createSampling: vi.fn(),
    computeSimilarityMetadata: vi.fn(),
    computeTypicalityMetadata: vi.fn()
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn()
    }
}));

const { toast } = await import('svelte-sonner');

describe('useCreateSelection', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('submit with diversity calls createSampling with correct args and resolves success', async () => {
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([
            {
                tag_id: 'tag-1',
                name: 'my-tag',
                kind: 'sample' as const,
                created_at: new Date(),
                updated_at: new Date()
            }
        ]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'diversity',
            nSamplesToSelect: 5,
            selectionResultTagName: 'my-tag',
            queryTagId: '',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(true);
        expect(createSampling).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                n_samples_to_select: 5,
                sampling_result_tag_name: 'my-tag',
                strategies: [{ strategy_name: 'diversity', embedding_model_name: null }],
                filter: undefined
            }
        });
        expect(loadTags).toHaveBeenCalled();
        expect(setTagSelected).toHaveBeenCalledWith('tag-1', true);
        expect(closeSelectionDialog).toHaveBeenCalled();
    });

    it('submit with typicality calls computeTypicalityMetadata first, then createSampling', async () => {
        vi.mocked(computeTypicalityMetadata).mockResolvedValue({ data: {}, error: null } as never);
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'typicality',
            nSamplesToSelect: 10,
            selectionResultTagName: 'result-tag',
            queryTagId: '',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(true);
        expect(computeTypicalityMetadata).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { embedding_model_name: null, metadata_name: 'typicality' }
        });
        expect(createSampling).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                n_samples_to_select: 10,
                sampling_result_tag_name: 'result-tag',
                strategies: [{ strategy_name: 'weights', metadata_key: 'typicality' }],
                filter: undefined
            }
        });
    });

    it('submit with similarity calls computeSimilarityMetadata first, then createSampling', async () => {
        vi.mocked(computeSimilarityMetadata).mockResolvedValue({ data: {}, error: null } as never);
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'similarity',
            nSamplesToSelect: 8,
            selectionResultTagName: 'sim-tag',
            queryTagId: 'query-tag-id',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(true);
        expect(computeSimilarityMetadata).toHaveBeenCalledWith({
            path: { collection_id: 'col-1', query_tag_id: 'query-tag-id' },
            body: { embedding_model_name: null, metadata_name: 'similarity' }
        });
        expect(createSampling).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                n_samples_to_select: 8,
                sampling_result_tag_name: 'sim-tag',
                strategies: [{ strategy_name: 'weights', metadata_key: 'similarity' }],
                filter: undefined
            }
        });
    });

    it('submit with similarity when isSimilaritySupported is false toasts error and returns false without calling API', async () => {
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: false,
            selectionStrategy: 'similarity',
            nSamplesToSelect: 8,
            selectionResultTagName: 'sim-tag',
            queryTagId: 'query-tag-id',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith(
            'Similarity is only available for image collections.'
        );
        expect(computeSimilarityMetadata).not.toHaveBeenCalled();
        expect(createSampling).not.toHaveBeenCalled();
    });

    it('API error in computeTypicalityMetadata toasts error and returns false without calling selection', async () => {
        vi.mocked(computeTypicalityMetadata).mockResolvedValue({
            data: null,
            error: { error: 'typicality failed' }
        } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'typicality',
            nSamplesToSelect: 10,
            selectionResultTagName: 'result-tag',
            queryTagId: '',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith(
            'Failed to compute typicality metadata: typicality failed'
        );
        expect(createSampling).not.toHaveBeenCalled();
    });

    it('API error in computeSimilarityMetadata toasts error and returns false without calling selection', async () => {
        vi.mocked(computeSimilarityMetadata).mockResolvedValue({
            data: null,
            error: { error: 'similarity failed' }
        } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'similarity',
            nSamplesToSelect: 8,
            selectionResultTagName: 'sim-tag',
            queryTagId: 'query-tag-id',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith(
            'Failed to compute similarity metadata: similarity failed'
        );
        expect(createSampling).not.toHaveBeenCalled();
    });

    it('API error in createSampling toasts error and returns false', async () => {
        vi.mocked(createSampling).mockResolvedValue({
            data: null,
            error: { error: 'selection failed' }
        } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'diversity',
            nSamplesToSelect: 5,
            selectionResultTagName: 'my-tag',
            queryTagId: '',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith('selection failed');
        expect(closeSelectionDialog).not.toHaveBeenCalled();
    });

    it('isSubmitting is true during submit and false after', async () => {
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const hook = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });

        let submittingDuringCall = false;
        vi.mocked(createSampling).mockImplementation(async () => {
            submittingDuringCall = get(hook.isSubmitting);
            return { data: {}, error: null } as never;
        });

        expect(get(hook.isSubmitting)).toBe(false);

        await hook.submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'diversity',
            nSamplesToSelect: 5,
            selectionResultTagName: 'my-tag',
            queryTagId: '',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(submittingDuringCall).toBe(true);
        expect(get(hook.isSubmitting)).toBe(false);
    });

    it('loadingMessage reflects the current step', async () => {
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const hook = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });

        const messages: string[] = [];
        vi.mocked(computeTypicalityMetadata).mockImplementation(async () => {
            messages.push(get(hook.loadingMessage));
            return { data: {}, error: null } as never;
        });
        vi.mocked(createSampling).mockImplementation(async () => {
            messages.push(get(hook.loadingMessage));
            return { data: {}, error: null } as never;
        });

        await hook.submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'typicality',
            nSamplesToSelect: 10,
            selectionResultTagName: 'result-tag',
            queryTagId: '',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(messages[0]).toBe('Computing typicality metadata...');
        expect(messages[1]).toBe('Creating selection...');
        expect(get(hook.loadingMessage)).toBe('');
    });

    it('submit with class_balancing and uniform mode calls createSampling with balance strategy', async () => {
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'class_balancing',
            nSamplesToSelect: 20,
            selectionResultTagName: 'balanced-tag',
            queryTagId: '',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(true);
        expect(createSampling).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                n_samples_to_select: 20,
                sampling_result_tag_name: 'balanced-tag',
                strategies: [{ strategy_name: 'balance', target_distribution: 'uniform' }],
                filter: undefined
            }
        });
        expect(computeTypicalityMetadata).not.toHaveBeenCalled();
        expect(computeSimilarityMetadata).not.toHaveBeenCalled();
    });

    it('submit with class_balancing and input mode passes input as target_distribution', async () => {
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'class_balancing',
            nSamplesToSelect: 15,
            selectionResultTagName: 'balanced-tag',
            queryTagId: '',
            balancingMode: 'input',
            selectionFilter: null
        });

        expect(result).toBe(true);
        expect(createSampling).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                n_samples_to_select: 15,
                sampling_result_tag_name: 'balanced-tag',
                strategies: [{ strategy_name: 'balance', target_distribution: 'input' }],
                filter: undefined
            }
        });
    });

    it('API error in createSampling for class_balancing toasts error and returns false', async () => {
        vi.mocked(createSampling).mockResolvedValue({
            data: null,
            error: { error: 'balance failed' }
        } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useCreateSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isSimilaritySupported: true,
            selectionStrategy: 'class_balancing',
            nSamplesToSelect: 20,
            selectionResultTagName: 'balanced-tag',
            queryTagId: '',
            balancingMode: 'uniform',
            selectionFilter: null
        });

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith('balance failed');
        expect(closeSelectionDialog).not.toHaveBeenCalled();
    });
});
