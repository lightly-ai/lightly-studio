import {
    createCombinationSelection,
    computeTypicalityMetadata
} from '$lib/api/lightly_studio_local/sdk.gen';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable, writable, type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CreateSelectionDialog from './CreateSelectionDialog.svelte';

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
        computeTypicalityMetadata: vi.fn()
    };
});

vi.mock('$lib/hooks/useTags/useTags', () => ({
    useTags: () => ({
        loadTags: vi.fn()
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

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        imageFilter: imageFilterStore
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

        const input = screen.getByTestId('selection-dialog-n-samples-input');
        await fireEvent.input(input, { target: { value: '10' } });

        expect(
            screen.getByTestId('selection-dialog-not-enough-samples-warning')
        ).toBeInTheDocument();
    });

    it('does not show the not enough samples warning when filteredSampleCount is 0', () => {
        render(CreateSelectionDialog);

        expect(
            screen.queryByTestId('selection-dialog-not-enough-samples-warning')
        ).not.toBeInTheDocument();
    });

    it('shows the no samples warning when filteredSampleCount is 0', () => {
        render(CreateSelectionDialog);

        expect(screen.getByTestId('selection-dialog-no-samples-warning')).toBeInTheDocument();
    });

    it('disables the submit button when filteredSampleCount is 0', () => {
        render(CreateSelectionDialog);

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
    });

    it('disables the submit button when requested count exceeds available samples', async () => {
        filteredSampleCountStore.set(5);

        render(CreateSelectionDialog);

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
});
