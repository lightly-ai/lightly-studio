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

const submitMock = vi.fn();
let isSubmittingStore: Writable<boolean>;
let loadingMessageStore: Writable<string>;

vi.mock('$lib/hooks/useCreateSelection/useCreateSelection', () => ({
    useCreateSelection: () => ({
        isSubmitting: isSubmittingStore,
        loadingMessage: loadingMessageStore,
        submit: submitMock
    })
}));

describe('CreateSelectionDialog', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        Element.prototype.scrollIntoView = vi.fn();
        pageMock.data.collection.sample_type = 'image';
        imageFilterStore = writable(null);
        videoFilterStore = writable(null);
        filteredSampleCountStore = writable(0);
        isSubmittingStore = writable(false);
        loadingMessageStore = writable('');
        tagsStore = writable([
            { tag_id: 'tag-1', name: 'Query Tag', description: null, kind: 'sample' as const }
        ]);
        submitMock.mockResolvedValue(undefined);
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

    it('submit button is disabled until strategy and tag name are both filled', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-diversity'));

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();

        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });

        expect(screen.getByTestId('selection-dialog-submit')).not.toBeDisabled();
    });

    it('calls submit with diversity strategy and image filter for image collections', async () => {
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
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    selectionStrategy: 'diversity',
                    selectionResultTagName: 'my-tag',
                    selectionFilter: expect.objectContaining({ filter_type: 'image' })
                })
            );
        });
    });

    it('calls submit with the video filter for video collections', async () => {
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
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    selectionFilter: expect.objectContaining({ filter_type: 'video' })
                })
            );
        });
    });

    it('calls submit with similarity strategy and the selected query tag', async () => {
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
            target: { value: 'sim-tag' }
        });
        await fireEvent.input(screen.getByTestId('selection-dialog-n-samples-input'), {
            target: { value: '20' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    selectionStrategy: 'similarity',
                    queryTagId: 'tag-1',
                    nSamplesToSelect: 20,
                    selectionResultTagName: 'sim-tag'
                })
            );
        });
    });

    it('calls submit with typicality strategy', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-typicality'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'typicality-tag' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    selectionStrategy: 'typicality',
                    selectionResultTagName: 'typicality-tag'
                })
            );
        });
    });

    it('calls submit with class_balancing strategy and uniform balancing mode', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-class-balancing'));
        await fireEvent.keyDown(screen.getByTestId('selection-dialog-balancing-mode-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-balancing-mode-uniform'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'balanced-tag' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    selectionStrategy: 'class_balancing',
                    balancingMode: 'uniform'
                })
            );
        });
    });

    it('shows input balancing mode as disabled and coming soon', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSelectionDialog);

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-class-balancing'));

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

    it('resets the form after a successful submission', async () => {
        submitMock.mockResolvedValue(true);
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
            expect(screen.getByTestId('selection-dialog-tag-name-input')).toHaveValue('');
        });
        expect(screen.getByTestId('selection-dialog-strategy-select')).toHaveTextContent(
            'Select strategy'
        );
    });

    it('does not reset the form when submission fails', async () => {
        submitMock.mockResolvedValue(false);
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
            expect(submitMock).toHaveBeenCalled();
        });
        expect(screen.getByTestId('selection-dialog-tag-name-input')).toHaveValue('my-tag');
        expect(screen.getByTestId('selection-dialog-strategy-select')).not.toHaveTextContent(
            'Select strategy'
        );
    });

    it('disables both buttons and shows loading message while submitting', async () => {
        isSubmittingStore.set(true);
        loadingMessageStore.set('Creating selection...');

        render(CreateSelectionDialog);

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
        expect(screen.getByTestId('selection-dialog-submit')).toHaveTextContent(
            'Creating selection...'
        );
        expect(screen.getByTestId('selection-dialog-cancel')).toBeDisabled();
    });

    it('shows "Creating..." on the submit button when submitting without a loading message', async () => {
        isSubmittingStore.set(true);

        render(CreateSelectionDialog);

        expect(screen.getByTestId('selection-dialog-submit')).toHaveTextContent('Creating...');
    });
});
