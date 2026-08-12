import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SamplesTab from './SamplesTab.svelte';

const pageMock = vi.hoisted(() => ({ params: { collection_id: 'test-collection' } }));
vi.mock('$app/state', () => ({ page: pageMock }));

const mocks = vi.hoisted(() => ({
    exportCollectionPrepare: vi.fn(),
    triggerDownload: vi.fn()
}));
vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionPrepare: mocks.exportCollectionPrepare
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

describe('SamplesTab', () => {
    beforeEach(() => {
        mocks.exportCollectionPrepare.mockReset();
        mocks.triggerDownload.mockReset();
    });

    it('calls the API with correct arguments on download', async () => {
        mocks.exportCollectionPrepare.mockResolvedValue({ data: { export_key: 'key123' } });
        render(SamplesTab);
        await fireEvent.click(screen.getByTestId('submit-button-samples'));
        await waitFor(() => {
            expect(mocks.exportCollectionPrepare).toHaveBeenCalledWith({
                path: { collection_id: 'test-collection' },
                body: { collection_filter: null }
            });
        });
    });

    it('triggers the download with the correct URL on success', async () => {
        mocks.exportCollectionPrepare.mockResolvedValue({ data: { export_key: 'key123' } });
        render(SamplesTab);
        await fireEvent.click(screen.getByTestId('submit-button-samples'));
        await waitFor(() => {
            expect(mocks.triggerDownload).toHaveBeenCalledWith(
                expect.stringContaining('/export/download/key123')
            );
        });
    });

    it('shows an error message when the API fails', async () => {
        mocks.exportCollectionPrepare.mockRejectedValue(new Error('Network error'));
        render(SamplesTab);
        await fireEvent.click(screen.getByTestId('submit-button-samples'));
        await waitFor(() => {
            expect(screen.getByText(/Export failed/)).toBeInTheDocument();
        });
    });

    it('shows an error message when the API returns an error body', async () => {
        mocks.exportCollectionPrepare.mockResolvedValue({ error: { message: 'Bad request' } });
        render(SamplesTab);
        await fireEvent.click(screen.getByTestId('submit-button-samples'));
        await waitFor(() => {
            expect(screen.getByText(/Export failed/)).toBeInTheDocument();
        });
    });

    it('calls onDownloadClick when the download button is clicked', async () => {
        mocks.exportCollectionPrepare.mockResolvedValue({ data: { export_key: 'key123' } });
        const onDownloadClick = vi.fn();
        render(SamplesTab, { props: { onDownloadClick } });
        await fireEvent.click(screen.getByTestId('submit-button-samples'));
        expect(onDownloadClick).toHaveBeenCalledOnce();
    });
});
