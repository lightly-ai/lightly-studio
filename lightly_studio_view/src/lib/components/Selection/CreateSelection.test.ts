import {
    createCombinationSelection,
    computeSimilarityMetadata,
    computeTypicalityMetadata
} from '$lib/api/lightly_studio_local/sdk.gen';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable, writable, type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CreateSelectionDialog from './CreateSelectionDialog.svelte';

type MockTag = {
    tag_id: string;
    name: string;
    description: string | null;
    kind: 'sample';
};

const pageMock = vi.hoisted(() => ({
    params: { collection_id: 'test-collection-id' },
    data: { collection: { sample_type: 'image' as string } }
}));

vi.mock('$app/state', () => ({
    page: pageMock
}));

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async () => {
    const actual = await vi.importActual('$lib/api/lightly_studio_local/sdk.gen');
    return {
        ...actual,
        createCombinationSelection: vi.fn(),
        computeSimilarityMetadata: vi.fn(),
        computeTypicalityMetadata: vi.fn()
    };
});

let tagsStore: Writable<MockTag[]>;
const loadTagsMock = vi.fn();
const setTagSelectedMock = vi.fn();

vi.mock('$lib/hooks/useTags/useTags', () => ({
    useTags: () => ({
        tags: tagsStore,
        loadTags: loadTagsMock,
        setTagSelected: setTagSelectedMock
    })
}));

vi.mock('$lib/hooks/useSelectionDialog/useSelectionDialog', () => ({
    useSelectionDialog: () => ({
        isSelectionDialogOpen: readable(true),
        openSelectionDialog: vi.fn(),
        closeSelectionDialog: vi.fn()
    })
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn()
    }
}));

let imageFilterStore: Writable<Record<string, unknown> | null>;
let videoFilterStore: Writable<Record<string, unknown> | null>;
let filteredSampleCountStore: Writable<number>;
const updateSortByMock = vi.fn();

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        imageFilter: imageFilterStore,
        updateSortBy: updateSortByMock
    })
}));

vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: () => ({
        videoFilter: videoFilterStore
    })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        filteredSampleCount: filteredSampleCountStore
    })
}));

const mockRequest = new Request('http://localhost');
const mockResponse = new Response(null, { status: 200 });

describe('CreateSelectionDialog', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        Element.prototype.scrollIntoView = vi.fn();
        pageMock.data.collection.sample_type = 'image';
        imageFilterStore = writable(null);
        videoFilterStore = writable(null);
        filteredSampleCountStore = writable(0);
        tagsStore = writable([
            { tag_id: 'tag-1', name: 'Query Tag', description: null, kind: 'sample' as const }
        ]);
        updateSortByMock.mockReset();
        loadTagsMock.mockReset();
        setTagSelectedMock.mockReset();

        loadTagsMock.mockImplementation(async () => {
            tagsStore.set([
                { tag_id: 'tag-1', name: 'Query Tag', description: null, kind: 'sample' },
                { tag_id: 'new-tag-id', name: 'my-tag', description: null, kind: 'sample' },
                {
                    tag_id: 'similarity-tag-id',
                    name: 'similarity-tag',
                    description: null,
                    kind: 'sample'
                }
            ]);
        });

        vi.mocked(createCombinationSelection).mockResolvedValue({
            data: undefined,
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
        vi.mocked(computeTypicalityMetadata).mockResolvedValue({
            data: undefined,
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
        vi.mocked(computeSimilarityMetadata).mockResolvedValue({
            data: 'similarity',
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
    });

    it('shows the filtered sample count in the header when filteredSampleCount is greater than 0', () => {
        filteredSampleCountStore.set(42);

        render(CreateSelectionDialog);

        expect(
            screen.getByText('Create a subset of the 42 samples fulfilling the current filters.')
        ).toBeInTheDocument();
    });

    it('shows the fallback header text when filteredSampleCount is 0', () => {
        render(CreateSelectionDialog);

        expect(
            screen.getByText('Create a subset of the samples fulfilling the current filters.')
        ).toBeInTheDocument();
    });

    it('shows the not enough samples warning when requested count exceeds available', async () => {
        filteredSampleCountStore.set(5);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-diversity'));

        const input = screen.getByTestId('selection-dialog-n-samples-input');
        await fireEvent.input(input, { target: { value: '10' } });

        expect(
            screen.getByTestId('selection-dialog-not-enough-samples-warning')
        ).toBeInTheDocument();
    });

    it('does not show the not enough samples warning when filteredSampleCount is 0', async () => {
        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-diversity'));

        expect(
            screen.queryByTestId('selection-dialog-not-enough-samples-warning')
        ).not.toBeInTheDocument();
    });

    it('shows the no samples warning when filteredSampleCount is 0', async () => {
        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-diversity'));

        expect(screen.getByTestId('selection-dialog-no-samples-warning')).toBeInTheDocument();
    });

    it('disables the submit button when filteredSampleCount is 0', async () => {
        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-diversity'));

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
    });

    it('disables the submit button when requested count exceeds available samples', async () => {
        filteredSampleCountStore.set(5);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-diversity'));

        const input = screen.getByTestId('selection-dialog-n-samples-input');
        await fireEvent.input(input, { target: { value: '10' } });

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
    });

    it('passes the image filter to the diversity selection API call for image collections', async () => {
        const imageFilter = { filter_type: 'image', sample_filter: { tag_ids: ['tag-1'] } };
        imageFilterStore.set(imageFilter);
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(createCombinationSelection).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({
                        filter: imageFilter
                    })
                })
            );
        });

        await waitFor(() => {
            expect(setTagSelectedMock).toHaveBeenCalledWith('new-tag-id', true);
        });
    });

    it('passes the video filter to the diversity selection API call for video collections', async () => {
        pageMock.data.collection.sample_type = 'video';
        const videoFilter = { filter_type: 'video', sample_filter: { tag_ids: ['tag-2'] } };
        videoFilterStore.set(videoFilter);
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(createCombinationSelection).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({
                        filter: videoFilter
                    })
                })
            );
        });
    });

    it('computes similarity metadata, applies similarity sorting, and creates selection', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-similarity'));
        await fireEvent.keyDown(screen.getByTestId('selection-dialog-query-tag-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-query-tag-tag-1'));

        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'similarity-tag' }
        });
        await fireEvent.input(screen.getByTestId('selection-dialog-n-samples-input'), {
            target: { value: '20' }
        });

        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(computeSimilarityMetadata).toHaveBeenCalledWith({
                path: { collection_id: 'test-collection-id', query_tag_id: 'tag-1' },
                body: {
                    embedding_model_name: null,
                    metadata_name: 'similarity'
                }
            });
        });

        await waitFor(() => {
            expect(createCombinationSelection).toHaveBeenCalledWith({
                path: { collection_id: 'test-collection-id' },
                body: expect.objectContaining({
                    n_samples_to_select: 20,
                    selection_result_tag_name: 'similarity-tag',
                    strategies: [
                        {
                            strategy_name: 'weights',
                            metadata_key: 'similarity'
                        }
                    ]
                })
            });
        });

        await waitFor(() => {
            expect(setTagSelectedMock).toHaveBeenCalledWith('similarity-tag-id', true);
        });
    });

    it('submits class balancing selections with uniform target distribution', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(
            await screen.findByTestId('selection-strategy-class-distribution')
        );

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-balancing-mode-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-balancing-mode-uniform'));

        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(createCombinationSelection).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: expect.objectContaining({
                        strategies: [
                            {
                                strategy_name: 'balance',
                                target_distribution: 'uniform'
                            }
                        ]
                    })
                })
            );
        });

        await waitFor(() => {
            expect(setTagSelectedMock).toHaveBeenCalledWith('new-tag-id', true);
        });
    });

    it('shows input balancing mode as disabled and coming soon', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(
            await screen.findByTestId('selection-strategy-class-distribution')
        );

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-balancing-mode-select'), {
            key: 'Enter'
        });
        const inputMode = await screen.findByTestId('selection-balancing-mode-input');
        expect(inputMode).toHaveAttribute('data-disabled');
        expect(inputMode).toHaveTextContent('Input (Coming soon)');
    });

    it('disables similarity for video collections', async () => {
        pageMock.data.collection.sample_type = 'video';

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('selection-strategy-similarity')).toHaveAttribute(
            'data-disabled'
        );
    });

    it('shows an empty state when no sample tags are available for similarity', async () => {
        tagsStore = writable([]);
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-similarity'));
        await fireEvent.keyDown(screen.getByTestId('selection-dialog-query-tag-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('selection-dialog-no-query-tags')).toHaveTextContent(
            'No sample tags available.'
        );
    });
});
