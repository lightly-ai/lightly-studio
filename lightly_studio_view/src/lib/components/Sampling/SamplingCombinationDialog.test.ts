import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable, writable, type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SamplingCombinationDialog from './SamplingCombinationDialog.svelte';

type MockTag = {
    tag_id: string;
    name: string;
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

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({
        metadataInfo: readable([])
    })
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({
        data: []
    })
}));

const submitMock = vi.fn();
let isSubmittingStore: Writable<boolean>;
let loadingMessageStore: Writable<string>;

vi.mock('$lib/hooks/useSubmitCombinationSelection/useSubmitCombinationSelection', () => ({
    useSubmitCombinationSelection: () => ({
        isSubmitting: isSubmittingStore,
        loadingMessage: loadingMessageStore,
        submit: submitMock
    })
}));

describe('SamplingCombinationDialog', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        Element.prototype.scrollIntoView = vi.fn();
        pageMock.data.collection.sample_type = 'image';
        imageFilterStore = writable(null);
        videoFilterStore = writable(null);
        filteredSampleCountStore = writable(0);
        isSubmittingStore = writable(false);
        loadingMessageStore = writable('');
        tagsStore = writable([{ tag_id: 'tag-1', name: 'Query Tag', kind: 'sample' as const }]);
        submitMock.mockResolvedValue(undefined);
    });

    it('shows the plural sample count in the header when filteredSampleCount is greater than 1', () => {
        filteredSampleCountStore.set(42);

        render(SamplingCombinationDialog);

        expect(screen.getByText('42 samples')).toBeInTheDocument();
    });

    it('shows the singular sample count in the header when filteredSampleCount is 1', () => {
        filteredSampleCountStore.set(1);

        render(SamplingCombinationDialog);

        expect(screen.getByText('1 sample')).toBeInTheDocument();
    });

    it('shows the count even when no samples match the filters', () => {
        render(SamplingCombinationDialog);

        expect(screen.getByText('0 samples')).toBeInTheDocument();
    });

    it('submit button is disabled when no strategies have been added', () => {
        filteredSampleCountStore.set(100);

        render(SamplingCombinationDialog);

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
    });

    it('submit button is disabled when strategies are added but tag name is empty', async () => {
        filteredSampleCountStore.set(100);

        render(SamplingCombinationDialog);

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
    });

    it('submit button is enabled when a strategy is added and tag name is filled', async () => {
        filteredSampleCountStore.set(100);

        render(SamplingCombinationDialog);

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });

        expect(screen.getByTestId('selection-dialog-submit')).not.toBeDisabled();
    });

    it('shows no samples warning when filteredSampleCount is 0', () => {
        render(SamplingCombinationDialog);

        expect(screen.getByTestId('selection-dialog-no-samples-warning')).toBeInTheDocument();
    });

    it('shows not enough samples warning when requested count exceeds available', async () => {
        filteredSampleCountStore.set(5);

        render(SamplingCombinationDialog);

        const input = screen.getByTestId('selection-dialog-n-samples-input');
        await fireEvent.input(input, { target: { value: '10' } });

        expect(
            screen.getByTestId('selection-dialog-not-enough-samples-warning')
        ).toBeInTheDocument();
    });

    it('does not show not enough samples warning when filteredSampleCount is 0', async () => {
        render(SamplingCombinationDialog);

        const input = screen.getByTestId('selection-dialog-n-samples-input');
        await fireEvent.input(input, { target: { value: '100' } });

        expect(
            screen.queryByTestId('selection-dialog-not-enough-samples-warning')
        ).not.toBeInTheDocument();
    });

    it('submit button is disabled when filteredSampleCount is 0', async () => {
        render(SamplingCombinationDialog);

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
    });

    it('submit button is disabled when not enough samples', async () => {
        filteredSampleCountStore.set(5);

        render(SamplingCombinationDialog);

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.input(screen.getByTestId('selection-dialog-n-samples-input'), {
            target: { value: '10' }
        });

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
    });

    it('calls submit with correct instances, count, tag name, and filter', async () => {
        submitMock.mockResolvedValue(false);
        const imageFilter = { filter_type: 'image', sample_filter: { tag_ids: ['tag-1'] } };
        imageFilterStore.set(imageFilter);
        filteredSampleCountStore.set(100);

        render(SamplingCombinationDialog);

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.input(screen.getByTestId('selection-dialog-n-samples-input'), {
            target: { value: '25' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    collectionId: 'test-collection-id',
                    isVideoCollection: false,
                    nSamplesToSelect: 25,
                    selectionResultTagName: 'my-tag',
                    selectionFilter: expect.objectContaining({ filter_type: 'image' }),
                    instances: expect.arrayContaining([
                        expect.objectContaining({ type: 'diversity' })
                    ])
                })
            );
        });
    });

    it('passes video filter for video collections', async () => {
        submitMock.mockResolvedValue(false);
        pageMock.data.collection.sample_type = 'video';
        const videoFilter = { filter_type: 'video', sample_filter: { tag_ids: ['tag-2'] } };
        videoFilterStore.set(videoFilter);
        filteredSampleCountStore.set(100);

        render(SamplingCombinationDialog);

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalledWith(
                expect.objectContaining({
                    isVideoCollection: true,
                    selectionFilter: expect.objectContaining({ filter_type: 'video' })
                })
            );
        });
    });

    it('resets the form after successful submission', async () => {
        submitMock.mockResolvedValue(true);
        filteredSampleCountStore.set(100);

        render(SamplingCombinationDialog);

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(screen.getByTestId('selection-dialog-tag-name-input')).toHaveValue('');
        });
    });

    it('does not reset the form when submission fails', async () => {
        submitMock.mockResolvedValue(false);
        filteredSampleCountStore.set(100);

        render(SamplingCombinationDialog);

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));
        await fireEvent.input(screen.getByTestId('selection-dialog-tag-name-input'), {
            target: { value: 'my-tag' }
        });
        await fireEvent.click(screen.getByTestId('selection-dialog-submit'));

        await waitFor(() => {
            expect(submitMock).toHaveBeenCalled();
        });
        expect(screen.getByTestId('selection-dialog-tag-name-input')).toHaveValue('my-tag');
    });

    it('disables both buttons and shows loading message while submitting', () => {
        isSubmittingStore.set(true);
        loadingMessageStore.set('Computing typicality metadata...');

        render(SamplingCombinationDialog);

        expect(screen.getByTestId('selection-dialog-submit')).toBeDisabled();
        expect(screen.getByTestId('selection-dialog-submit')).toHaveTextContent(
            'Computing typicality metadata...'
        );
        expect(screen.getByTestId('selection-dialog-cancel')).toBeDisabled();
    });

    it('shows Creating... on the submit button when submitting without a loading message', () => {
        isSubmittingStore.set(true);

        render(SamplingCombinationDialog);

        expect(screen.getByTestId('selection-dialog-submit')).toHaveTextContent('Creating...');
    });
});
