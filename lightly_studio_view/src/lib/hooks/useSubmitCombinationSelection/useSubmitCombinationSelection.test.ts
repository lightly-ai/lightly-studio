import { createSampling } from '$lib/api/lightly_studio_local/sdk.gen';
import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSubmitCombinationSelection } from './useSubmitCombinationSelection';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    createSampling: vi.fn()
}));

vi.mock('svelte-sonner', () => ({
    toast: { error: vi.fn(), success: vi.fn() }
}));

const mockTrackEvent = vi.fn();
vi.mock('$lib/hooks', () => ({
    usePostHog: () => ({ trackEvent: mockTrackEvent })
}));

const { toast } = await import('svelte-sonner');

describe('useSubmitCombinationSelection', () => {
    const defaultHookParams = {
        tags: writable([]),
        setTagSelected: vi.fn(),
        loadTags: vi.fn().mockResolvedValue(undefined),
        closeSelectionDialog: vi.fn(),
        filteredSampleCount: writable(100)
    };

    const defaultSubmitParams = {
        collectionId: 'col-1',
        isVideoCollection: false,
        instances: [
            { id: 'inst-1', type: 'diversity' as const, params: { strength: 1 }, isExpanded: true }
        ],
        nSamplesToSelect: 10,
        selectionResultTagName: 'my-tag',
        selectionFilter: null
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('submits metadata preparation and selection together', async () => {
        vi.mocked(createSampling).mockResolvedValue({
            data: undefined,
            request: new Request('http://localhost'),
            response: new Response(null, { status: 204 })
        });
        const { submit } = useSubmitCombinationSelection({ ...defaultHookParams });
        const call = submit({
            ...defaultSubmitParams,
            instances: [
                { id: 'typ', type: 'typicality', params: { strength: 1 }, isExpanded: true },
                {
                    id: 'sim',
                    type: 'similarity',
                    params: { strength: 2, query_tag_id: 'query' },
                    isExpanded: true
                }
            ]
        });
        expect(createSampling).toHaveBeenCalledTimes(1);
        expect(createSampling).toHaveBeenCalledWith(
            expect.objectContaining({
                body: expect.objectContaining({
                    sampling_result_tag_name: 'my-tag',
                    metadata_computations: [
                        { kind: 'typicality', metadata_name: 'typicality-typ' },
                        {
                            kind: 'similarity',
                            metadata_name: 'similarity-sim',
                            query_tag_id: 'query'
                        }
                    ],
                    strategies: [
                        { strategy_name: 'weights', metadata_key: 'typicality-typ', strength: 1 },
                        { strategy_name: 'weights', metadata_key: 'similarity-sim', strength: 2 }
                    ]
                })
            })
        );
        expect(await call).toBe(true);
    });

    it('rejects similarity for video collections before submitting', async () => {
        const { submit } = useSubmitCombinationSelection({ ...defaultHookParams });
        expect(
            await submit({
                ...defaultSubmitParams,
                isVideoCollection: true,
                instances: [
                    {
                        id: 'sim',
                        type: 'similarity',
                        params: { strength: 1, query_tag_id: 'query' },
                        isExpanded: true
                    }
                ]
            })
        ).toBe(false);
        expect(createSampling).not.toHaveBeenCalled();
    });

    it('calls createSampling with mapped strategies, count, tag name, and filter', async () => {
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const selectionFilter = {
            filter_type: 'image' as const,
            sample_filter: { tag_ids: ['tag-1'] }
        };

        const { submit } = useSubmitCombinationSelection({ ...defaultHookParams });
        await submit({
            ...defaultSubmitParams,
            nSamplesToSelect: 20,
            selectionResultTagName: 'result-tag',
            selectionFilter
        });

        expect(createSampling).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: {
                n_samples_to_select: 20,
                sampling_result_tag_name: 'result-tag',
                strategies: [
                    { strategy_name: 'diversity', embedding_model_name: null, strength: 1 }
                ],
                metadata_computations: [],
                filter: selectionFilter
            }
        });
    });

    it('passes the preselected tag to createSampling', async () => {
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);

        const { submit } = useSubmitCombinationSelection({ ...defaultHookParams });
        await submit({ ...defaultSubmitParams, preselectedTagId: 'preselected-tag' });

        expect(createSampling).toHaveBeenCalledWith(
            expect.objectContaining({
                body: expect.objectContaining({ preselected_tag_id: 'preselected-tag' })
            })
        );
    });

    it('returns false and toasts error when createSampling fails', async () => {
        vi.mocked(createSampling).mockResolvedValue({
            data: undefined,
            error: { error: 'Server error' }
        } as never);
        const loadTags = vi.fn();
        const closeSelectionDialog = vi.fn();

        const { submit } = useSubmitCombinationSelection({
            ...defaultHookParams,
            loadTags,
            closeSelectionDialog
        });
        const result = await submit({ ...defaultSubmitParams, selectionResultTagName: 'fail-tag' });

        expect(result).toBe(false);
        expect(toast.error).toHaveBeenCalledWith('Server error');
        expect(loadTags).not.toHaveBeenCalled();
        expect(closeSelectionDialog).not.toHaveBeenCalled();
    });

    it('on success: reloads tags, selects matching new tag, closes dialog, shows toast', async () => {
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const setTagSelected = vi.fn();
        const closeSelectionDialog = vi.fn();
        const tags = writable([
            {
                tag_id: 'tag-abc',
                name: 'new-tag',
                kind: 'sample' as const,
                created_at: new Date(),
                updated_at: new Date()
            }
        ]);

        const { submit } = useSubmitCombinationSelection({
            ...defaultHookParams,
            tags,
            loadTags,
            setTagSelected,
            closeSelectionDialog
        });
        const result = await submit({ ...defaultSubmitParams, selectionResultTagName: 'new-tag' });

        expect(result).toBe(true);
        expect(toast.success).toHaveBeenCalledWith('Sampling created successfully');
        expect(loadTags).toHaveBeenCalled();
        expect(setTagSelected).toHaveBeenCalledWith('tag-abc', true);
        expect(closeSelectionDialog).toHaveBeenCalled();
    });

    it('sets isSubmitting to true while running and false when done', async () => {
        let resolveApi!: (value: unknown) => void;
        vi.mocked(createSampling).mockReturnValueOnce(
            new Promise((resolve) => {
                resolveApi = resolve;
            }) as never
        );

        const { isSubmitting, submit } = useSubmitCombinationSelection({ ...defaultHookParams });

        expect(get(isSubmitting)).toBe(false);
        const call = submit({
            ...defaultSubmitParams,
            nSamplesToSelect: 5,
            selectionResultTagName: 'tag'
        });
        expect(get(isSubmitting)).toBe(true);

        resolveApi({ data: {}, error: null });
        expect(await call).toBe(true);
        expect(get(isSubmitting)).toBe(false);
    });

    it('tracks sampling_submitted with filteredSampleCount from params', async () => {
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const filteredSampleCount = writable(42);

        const { submit } = useSubmitCombinationSelection({
            ...defaultHookParams,
            filteredSampleCount
        });
        await submit({ ...defaultSubmitParams });

        expect(mockTrackEvent).toHaveBeenCalledWith(
            'sampling_submitted',
            expect.objectContaining({ filtered_sample_count: 42 })
        );
    });

    it('tracks sampling_triggered with success: true before closing the dialog', async () => {
        vi.mocked(createSampling).mockResolvedValue({ data: {}, error: null } as never);
        const closeSelectionDialog = vi.fn();
        const callOrder: string[] = [];

        mockTrackEvent.mockImplementation((event: string) => {
            if (event === 'sampling_triggered') callOrder.push('track');
        });
        closeSelectionDialog.mockImplementation(() => callOrder.push('close'));

        const { submit } = useSubmitCombinationSelection({
            ...defaultHookParams,
            closeSelectionDialog
        });
        await submit({ ...defaultSubmitParams });

        expect(mockTrackEvent).toHaveBeenCalledWith(
            'sampling_triggered',
            expect.objectContaining({ success: true })
        );
        expect(callOrder).toEqual(['track', 'close']);
    });

    it('concurrent submit guard: second call while submitting returns false immediately', async () => {
        let resolveFirst!: (value: unknown) => void;
        vi.mocked(createSampling).mockReturnValueOnce(
            new Promise((resolve) => {
                resolveFirst = resolve;
            }) as never
        );

        const { submit } = useSubmitCombinationSelection({ ...defaultHookParams });
        const submitParams = {
            ...defaultSubmitParams,
            instances: [
                {
                    id: 'inst-1',
                    type: 'diversity' as const,
                    params: { strength: 1 },
                    isExpanded: true
                }
            ],
            nSamplesToSelect: 5,
            selectionResultTagName: 'tag'
        };

        const firstCall = submit(submitParams);
        const secondResult = await submit(submitParams);

        expect(secondResult).toBe(false);

        resolveFirst({ data: {}, error: null });
        await firstCall;

        expect(createSampling).toHaveBeenCalledTimes(1);
    });
});
