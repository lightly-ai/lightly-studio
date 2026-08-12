import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CaptionsTab from './CaptionsTab.svelte';

const pageMock = vi.hoisted(() => ({ params: { collection_id: 'test-collection' } }));
vi.mock('$app/state', () => ({ page: pageMock }));

const mocks = vi.hoisted(() => ({
    exportCollectionCaptionsPrepare: vi.fn(),
    triggerDownload: vi.fn()
}));
vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionCaptionsPrepare: mocks.exportCollectionCaptionsPrepare
}));

const imageFilterStore = writable(null);
vi.mock('$lib/hooks', () => ({
    useImageFilters: () => ({ imageFilter: imageFilterStore })
}));

vi.mock('../useExportDownload', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../useExportDownload')>();
    return {
        ...actual,
        triggerDownload: mocks.triggerDownload
    };
});

describe('CaptionsTab', () => {
    beforeEach(() => {
        mocks.exportCollectionCaptionsPrepare.mockReset();
        mocks.triggerDownload.mockReset();
    });

    it('renders the description', () => {
        render(CaptionsTab);
        expect(
            screen.getByText('The captions will be exported in COCO format.')
        ).toBeInTheDocument();
    });

    it('calls the API with correct arguments on download', async () => {
        mocks.exportCollectionCaptionsPrepare.mockResolvedValue({ data: { export_key: 'key123' } });
        render(CaptionsTab);
        await fireEvent.click(screen.getByTestId('submit-button-captions'));
        await waitFor(() => {
            expect(mocks.exportCollectionCaptionsPrepare).toHaveBeenCalledWith({
                path: { collection_id: 'test-collection' },
                body: { image_filter: null }
            });
        });
    });

    it('triggers the download with the correct URL on success', async () => {
        mocks.exportCollectionCaptionsPrepare.mockResolvedValue({ data: { export_key: 'key123' } });
        render(CaptionsTab);
        await fireEvent.click(screen.getByTestId('submit-button-captions'));
        await waitFor(() => {
            expect(mocks.triggerDownload).toHaveBeenCalledWith(
                expect.stringContaining('/export/download/key123')
            );
        });
    });

    it('shows an error message when the API fails', async () => {
        mocks.exportCollectionCaptionsPrepare.mockRejectedValue(new Error('Network error'));
        render(CaptionsTab);
        await fireEvent.click(screen.getByTestId('submit-button-captions'));
        await waitFor(() => {
            expect(screen.getByText(/Export failed/)).toBeInTheDocument();
        });
    });

    it('shows an error message when the API returns an error body', async () => {
        mocks.exportCollectionCaptionsPrepare.mockResolvedValue({
            error: { message: 'Bad request' }
        });
        render(CaptionsTab);
        await fireEvent.click(screen.getByTestId('submit-button-captions'));
        await waitFor(() => {
            expect(screen.getByText(/Export failed/)).toBeInTheDocument();
        });
    });

    it('calls onDownloadClick when the download button is clicked', async () => {
        mocks.exportCollectionCaptionsPrepare.mockResolvedValue({ data: { export_key: 'key123' } });
        const onDownloadClick = vi.fn();
        render(CaptionsTab, { props: { onDownloadClick } });
        await fireEvent.click(screen.getByTestId('submit-button-captions'));
        expect(onDownloadClick).toHaveBeenCalledOnce();
    });
});
