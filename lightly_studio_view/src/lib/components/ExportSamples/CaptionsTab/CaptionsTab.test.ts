import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CaptionsTab from './CaptionsTab.svelte';

const pageMock = vi.hoisted(() => ({ params: { collection_id: 'test-collection' } }));
vi.mock('$app/state', () => ({ page: pageMock }));

const mocks = vi.hoisted(() => ({
    exportCollectionCaptionsPrepare: vi.fn()
}));
vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionCaptionsPrepare: mocks.exportCollectionCaptionsPrepare
}));

const imageFilterStore = writable(null);
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({ imageFilter: imageFilterStore })
}));

describe('CaptionsTab', () => {
    let openSpy: ReturnType<typeof vi.spyOn<typeof window, 'open'>> | undefined;

    beforeEach(() => {
        mocks.exportCollectionCaptionsPrepare.mockReset();
    });

    afterEach(() => openSpy?.mockRestore());

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

    it('opens a new tab with the download URL on success', async () => {
        openSpy = vi.spyOn(window, 'open').mockReturnValue(null);
        mocks.exportCollectionCaptionsPrepare.mockResolvedValue({ data: { export_key: 'key123' } });
        render(CaptionsTab);
        await fireEvent.click(screen.getByTestId('submit-button-captions'));
        await waitFor(() => {
            expect(openSpy).toHaveBeenCalledWith(
                expect.stringContaining('/export/download/key123'),
                '_blank'
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
});
