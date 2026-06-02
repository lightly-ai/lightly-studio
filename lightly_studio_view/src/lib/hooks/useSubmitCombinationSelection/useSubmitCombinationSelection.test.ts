import { createCombinationSelection } from '$lib/api/lightly_studio_local/sdk.gen';
import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSubmitCombinationSelection } from './useSubmitCombinationSelection';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    createCombinationSelection: vi.fn()
}));

vi.mock('./computeStrategyMetadata', () => ({
    computeStrategyMetadata: vi.fn().mockResolvedValue(true)
}));

vi.mock('./strategyApiMapping', () => ({
    toApiStrategy: vi.fn((instance) => ({ strategy_name: 'diversity', _id: instance.id }))
}));

vi.mock('svelte-sonner', () => ({
    toast: { error: vi.fn(), success: vi.fn() }
}));

const { toast } = await import('svelte-sonner');
const { computeStrategyMetadata } = await import('./computeStrategyMetadata');

describe('useSubmitCombinationSelection', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(computeStrategyMetadata).mockResolvedValue(true);
    });

    it('calls computeStrategyMetadata for each instance with collectionId and isVideoCollection', async () => {
        vi.mocked(createCombinationSelection).mockResolvedValue({ data: {}, error: null } as never);
        const tagsStore = writable([]);

        const { submit } = useSubmitCombinationSelection({
            tags: tagsStore,
            setTagSelected: vi.fn(),
            loadTags: vi.fn().mockResolvedValue(undefined),
            closeSelectionDialog: vi.fn()
        });
        await submit({
            collectionId: 'col-1',
            isVideoCollection: false,
            instances: [
                { id: 'inst-a', type: 'diversity', params: { strength: 1 }, isExpanded: true },
                { id: 'inst-b', type: 'typicality', params: { strength: 1 }, isExpanded: true }
            ],
            nSamplesToSelect: 10,
            selectionResultTagName: 'my-tag',
            selectionFilter: null
        });

        expect(computeStrategyMetadata).toHaveBeenCalledTimes(2);
        expect(computeStrategyMetadata).toHaveBeenCalledWith(
            expect.objectContaining({ id: 'inst-a' }),
            'col-1',
            false,
            expect.any(Function)
        );
        expect(computeStrategyMetadata).toHaveBeenCalledWith(
            expect.objectContaining({ id: 'inst-b' }),
            'col-1',
            false,
            expect.any(Function)
        );
    });

    it('stops and returns false without calling createCombinationSelection when metadata computation fails', async () => {
        vi.mocked(computeStrategyMetadata).mockResolvedValue(false);
        const tagsStore = writable([]);

        const { submit } = useSubmitCombinationSelection({
            tags: tagsStore,
            setTagSelected: vi.fn(),
            loadTags: vi.fn(),
            closeSelectionDialog: vi.fn()
        });
        const result = await submit({
            collectionId: 'col-1',
            isVideoCollection: false,
            instances: [
                { id: 'inst-1', type: 'typicality', params: { strength: 1 }, isExpanded: true }
            ],
            nSamplesToSelect: 5,
            selectionResultTagName: 'fail-tag',
            selectionFilter: null
        });

        expect(result).toBe(false);
        expect(createCombinationSelection).not.toHaveBeenCalled();
    });

    it('calls createCombinationSelection with mapped strategies, count, tag name, and filter', async () => {
        vi.mocked(createCombinationSelection).mockResolvedValue({ data: {}, error: null } as never);
        const selectionFilter = {
            filter_type: 'image' as const,
            sample_filter: { tag_ids: ['tag-1'] }
        };
        const tagsStore = writable([]);

        const { submit } = useSubmitCombinationSelection({
            tags: tagsStore,
            setTagSelected: vi.fn(),
            loadTags: vi.fn().mockResolvedValue(undefined),
            closeSelectionDialog: vi.fn()
        });
        await submit({
            collectionId: 'col-1',
            isVideoCollection: false,
            instances: [
                { id: 'inst-1', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ],
            nSamplesToSelect: 20,
            selectionResultTagName: 'result-tag',
            selectionFilter
        });

        expect(createCombinationSelection).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                n_samples_to_select: 20,
                selection_result_tag_name: 'result-tag',
                strategies: [{ strategy_name: 'diversity', _id: 'inst-1' }],
                filter: selectionFilter
            }
        });
    });

    it('returns false and toasts error when createCombinationSelection fails', async () => {
        vi.mocked(createCombinationSelection).mockResolvedValue({
            data: undefined,
            error: { error: 'Server error' }
        } as never);
        const loadTags = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([]);

        const { submit } = useSubmitCombinationSelection({
            tags: tagsStore,
            setTagSelected: vi.fn(),
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isVideoCollection: false,
            instances: [
                { id: 'inst-1', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ],
            nSamplesToSelect: 5,
            selectionResultTagName: 'fail-tag',
            selectionFilter: null
        });

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith('Server error');
        expect(loadTags).not.toHaveBeenCalled();
        expect(closeSelectionDialog).not.toHaveBeenCalled();
    });

    it('on success: reloads tags, selects matching new tag, closes dialog, shows toast', async () => {
        vi.mocked(createCombinationSelection).mockResolvedValue({ data: {}, error: null } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tagsStore = writable([
            {
                tag_id: 'tag-abc',
                name: 'new-tag',
                kind: 'sample' as const,
                created_at: new Date(),
                updated_at: new Date()
            }
        ]);

        const { submit } = useSubmitCombinationSelection({
            tags: tagsStore,
            setTagSelected,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({
            collectionId: 'col-1',
            isVideoCollection: false,
            instances: [
                { id: 'inst-1', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ],
            nSamplesToSelect: 10,
            selectionResultTagName: 'new-tag',
            selectionFilter: null
        });

        expect(result).toBe(true);
        expect(toast.success).toHaveBeenCalledWith('Selection created successfully');
        expect(loadTags).toHaveBeenCalled();
        expect(setTagSelected).toHaveBeenCalledWith('tag-abc', true);
        expect(closeSelectionDialog).toHaveBeenCalled();
    });

    it('sets isSubmitting to true while running and false when done', async () => {
        let resolveApi!: (value: unknown) => void;
        vi.mocked(createCombinationSelection).mockReturnValueOnce(
            new Promise((resolve) => {
                resolveApi = resolve;
            }) as never
        );
        const tagsStore = writable([]);

        const { isSubmitting, submit } = useSubmitCombinationSelection({
            tags: tagsStore,
            setTagSelected: vi.fn(),
            loadTags: vi.fn().mockResolvedValue(undefined),
            closeSelectionDialog: vi.fn()
        });

        expect(get(isSubmitting)).toBe(false);
        const call = submit({
            collectionId: 'col-1',
            isVideoCollection: false,
            instances: [
                { id: 'inst-1', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ],
            nSamplesToSelect: 5,
            selectionResultTagName: 'tag',
            selectionFilter: null
        });
        expect(get(isSubmitting)).toBe(true);

        resolveApi({ data: {}, error: null });
        await call;
        expect(get(isSubmitting)).toBe(false);
    });

    it('forwards the onProgress callback to computeStrategyMetadata which updates loadingMessage', async () => {
        vi.mocked(computeStrategyMetadata).mockImplementationOnce(
            async (_instance, _collectionId, _isVideo, onProgress) => {
                onProgress('Computing typicality metadata...');
                return true;
            }
        );
        vi.mocked(createCombinationSelection).mockResolvedValue({ data: {}, error: null } as never);
        const tagsStore = writable([]);

        const { loadingMessage, submit } = useSubmitCombinationSelection({
            tags: tagsStore,
            setTagSelected: vi.fn(),
            loadTags: vi.fn().mockResolvedValue(undefined),
            closeSelectionDialog: vi.fn()
        });

        const messages: string[] = [];
        loadingMessage.subscribe((msg) => messages.push(msg));

        await submit({
            collectionId: 'col-1',
            isVideoCollection: false,
            instances: [
                { id: 'inst-1', type: 'typicality', params: { strength: 1 }, isExpanded: true }
            ],
            nSamplesToSelect: 5,
            selectionResultTagName: 'tag',
            selectionFilter: null
        });

        expect(messages).toContain('Computing typicality metadata...');
    });

    it('concurrent submit guard: second call while submitting returns false immediately', async () => {
        let resolveFirst!: (value: unknown) => void;
        vi.mocked(createCombinationSelection).mockReturnValueOnce(
            new Promise((resolve) => {
                resolveFirst = resolve;
            }) as never
        );
        const tagsStore = writable([]);

        const { submit } = useSubmitCombinationSelection({
            tags: tagsStore,
            setTagSelected: vi.fn(),
            loadTags: vi.fn(),
            closeSelectionDialog: vi.fn()
        });
        const submitParams = {
            collectionId: 'col-1',
            isVideoCollection: false,
            instances: [
                {
                    id: 'inst-1',
                    type: 'diversity' as const,
                    params: { strength: 1 },
                    isExpanded: true
                }
            ],
            nSamplesToSelect: 5,
            selectionResultTagName: 'tag',
            selectionFilter: null
        };

        const firstCall = submit(submitParams);
        const secondResult = await submit(submitParams);

        expect(secondResult).toBe(false);
        expect(createCombinationSelection).toHaveBeenCalledTimes(1);

        resolveFirst({ data: {}, error: null });
        await firstCall;
    });
});
