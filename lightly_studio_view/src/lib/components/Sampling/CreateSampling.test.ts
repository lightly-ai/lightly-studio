import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable, writable, type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CreateSamplingDialog from './CreateSamplingDialog.svelte';

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

vi.mock('$lib/hooks/useSamplingDialog/useSamplingDialog', () => ({
    useSamplingDialog: () => ({
        isSamplingDialogOpen: readable(true),
        openSamplingDialog: vi.fn(),
        closeSamplingDialog: vi.fn()
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

vi.mock('$lib/hooks/useCreateSampling/useCreateSampling', () => ({
    useCreateSampling: () => ({
        isSubmitting: isSubmittingStore,
        loadingMessage: loadingMessageStore,
        submit: submitMock
    })
}));

describe('CreateSamplingDialog', () => {
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

        render(CreateSamplingDialog);

        expect(
            screen.getByText('Create a subset of the 42 samples fulfilling the current filters.')
        ).toBeInTheDocument();
    });

    it('shows the fallback header text when filteredSampleCount is 0', () => {
        render(CreateSamplingDialog);

        expect(
            screen.getByText('Create a subset of the samples fulfilling the current filters.')
        ).toBeInTheDocument();
    });

    it('shows the not enough samples warning when requested count exceeds available', async () => {
        filteredSampleCountStore.set(5);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));

        const input = screen.getByTestId('sampling-dialog-n-samples-input');
        await fireEvent.input(input, { target: { value: '10' } });

        expect(
            screen.getByTestId('sampling-dialog-not-enough-samples-warning')
        ).toBeInTheDocument();
    });

    it('does not show the not enough samples warning when filteredSampleCount is 0', async () => {
        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));

        expect(
            screen.queryByTestId('sampling-dialog-not-enough-samples-warning')
        ).not.toBeInTheDocument();
    });

    it('shows the no samples warning when filteredSampleCount is 0', async () => {
        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));

        expect(screen.getByTestId('sampling-dialog-no-samples-warning')).toBeInTheDocument();
    });

    it('disables the submit button when filteredSampleCount is 0', async () => {
        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));

        expect(screen.getByTestId('sampling-dialog-submit')).toBeDisabled();
    });

    it('disables the submit button when requested count exceeds available samples', async () => {
        filteredSampleCountStore.set(5);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));

        const input = screen.getByTestId('sampling-dialog-n-samples-input');
        await fireEvent.input(input, { target: { value: '10' } });

        expect(screen.getByTestId('sampling-dialog-submit')).toBeDisabled();
    });

    it('submit button is disabled until strategy and tag name are both filled', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        expect(screen.getByTestId('sampling-dialog-submit')).toBeDisabled();

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));

        expect(screen.getByTestId('sampling-dialog-submit')).toBeDisabled();

        await fireEvent.input(screen.getByTestId('sampling-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });

        expect(screen.getByTestId('sampling-dialog-submit')).not.toBeDisabled();
    });

    it('calls submit with diversity strategy and image filter for image collections', async () => {
        const imageFilter = { filter_type: 'image', sample_filter: { tag_ids: ['tag-1'] } };
        imageFilterStore.set(imageFilter);
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('sampling-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('sampling-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    samplingStrategy: 'diversity',
                    samplingResultTagName: 'my-tag',
                    samplingFilter: expect.objectContaining({ filter_type: 'image' })
                })
            );
        });
    });

    it('calls submit with the video filter for video collections', async () => {
        pageMock.data.collection.sample_type = 'video';
        const videoFilter = { filter_type: 'video', sample_filter: { tag_ids: ['tag-2'] } };
        videoFilterStore.set(videoFilter);
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('sampling-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('sampling-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    samplingFilter: expect.objectContaining({ filter_type: 'video' })
                })
            );
        });
    });

    it('calls submit with similarity strategy and the selected query tag', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-similarity'));
        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-query-tag-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-query-tag-tag-1'));
        await fireEvent.input(screen.getByTestId('sampling-dialog-tag-name-input'), {
            target: { value: 'sim-tag' }
        });
        await fireEvent.input(screen.getByTestId('sampling-dialog-n-samples-input'), {
            target: { value: '20' }
        });
        await fireEvent.click(screen.getByTestId('sampling-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    samplingStrategy: 'similarity',
                    queryTagId: 'tag-1',
                    nSamplesToSelect: 20,
                    samplingResultTagName: 'sim-tag'
                })
            );
        });
    });

    it('calls submit with typicality strategy', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-typicality'));
        await fireEvent.input(screen.getByTestId('sampling-dialog-tag-name-input'), {
            target: { value: 'typicality-tag' }
        });
        await fireEvent.click(screen.getByTestId('sampling-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    samplingStrategy: 'typicality',
                    samplingResultTagName: 'typicality-tag'
                })
            );
        });
    });

    it('calls submit with class_balancing strategy and uniform balancing mode', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-class-balancing'));
        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-balancing-mode-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-balancing-mode-uniform'));
        await fireEvent.input(screen.getByTestId('sampling-dialog-tag-name-input'), {
            target: { value: 'balanced-tag' }
        });
        await fireEvent.click(screen.getByTestId('sampling-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    samplingStrategy: 'class_balancing',
                    balancingMode: 'uniform'
                })
            );
        });
    });

    it('shows input balancing mode as disabled and coming soon', async () => {
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-class-balancing'));

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-balancing-mode-select'), {
            key: 'Enter'
        });
        const inputMode = await screen.findByTestId('sampling-balancing-mode-input');
        expect(inputMode).toHaveAttribute('data-disabled');
        expect(inputMode).toHaveTextContent('Input (Coming soon)');
    });

    it('disables similarity for video collections', async () => {
        pageMock.data.collection.sample_type = 'video';

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('sampling-strategy-similarity')).toHaveAttribute(
            'data-disabled'
        );
    });

    it('shows an empty state when no sample tags are available for similarity', async () => {
        tagsStore = writable([]);
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-similarity'));
        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-query-tag-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('sampling-dialog-no-query-tags')).toHaveTextContent(
            'No sample tags available.'
        );
    });

    it('resets the form after a successful submission', async () => {
        submitMock.mockResolvedValue(true);
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('sampling-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('sampling-dialog-submit'));

        await waitFor(() => {
            expect(screen.getByTestId('sampling-dialog-tag-name-input')).toHaveValue('');
        });
        expect(screen.getByTestId('sampling-dialog-strategy-select')).toHaveTextContent(
            'Select strategy'
        );
    });

    it('does not reset the form when submission fails', async () => {
        submitMock.mockResolvedValue(false);
        filteredSampleCountStore.set(100);

        render(CreateSamplingDialog);

        await fireEvent.keyDown(screen.getByTestId('sampling-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('sampling-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('sampling-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('sampling-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalled();
        });
        expect(screen.getByTestId('sampling-dialog-tag-name-input')).toHaveValue('my-tag');
        expect(screen.getByTestId('sampling-dialog-strategy-select')).not.toHaveTextContent(
            'Select strategy'
        );
    });

    it('disables both buttons and shows loading message while submitting', async () => {
        isSubmittingStore.set(true);
        loadingMessageStore.set('Creating sampling...');

        render(CreateSamplingDialog);

        expect(screen.getByTestId('sampling-dialog-submit')).toBeDisabled();
        expect(screen.getByTestId('sampling-dialog-submit')).toHaveTextContent(
            'Creating sampling...'
        );
        expect(screen.getByTestId('sampling-dialog-cancel')).toBeDisabled();
    });

    it('shows "Creating..." on the submit button when submitting without a loading message', async () => {
        isSubmittingStore.set(true);

        render(CreateSamplingDialog);

        expect(screen.getByTestId('sampling-dialog-submit')).toHaveTextContent('Creating...');
    });
});
