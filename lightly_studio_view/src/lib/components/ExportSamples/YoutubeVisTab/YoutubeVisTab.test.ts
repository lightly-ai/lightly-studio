import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import YoutubeVisTab from './YoutubeVisTab.svelte';

const pageMock = vi.hoisted(() => ({ params: { collection_id: 'test-collection' } }));
vi.mock('$app/state', () => ({ page: pageMock }));

const mocks = vi.hoisted(() => ({
    exportCollectionYoutubeVisPrepare: vi.fn()
}));
vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionYoutubeVisPrepare: mocks.exportCollectionYoutubeVisPrepare
}));

describe('YoutubeVisTab', () => {
    beforeEach(() => {
        mocks.exportCollectionYoutubeVisPrepare.mockReset();
    });

    it('renders the description', () => {
        render(YoutubeVisTab);
        expect(screen.getByText(/YouTube-VIS format/)).toBeInTheDocument();
    });

    it('calls the API with correct arguments on download', async () => {
        vi.spyOn(window, 'open').mockReturnValue(null);
        mocks.exportCollectionYoutubeVisPrepare.mockResolvedValue({
            data: { export_key: 'key123' }
        });
        render(YoutubeVisTab);
        await fireEvent.click(
            screen.getByTestId('submit-button-youtube-vis-instance-segmentations')
        );
        expect(mocks.exportCollectionYoutubeVisPrepare).toHaveBeenCalledWith({
            path: { collection_id: 'test-collection' },
            body: { video_filter: null }
        });
    });

    it('opens a new tab with the download URL on success', async () => {
        const openSpy = vi.spyOn(window, 'open').mockReturnValue(null);
        mocks.exportCollectionYoutubeVisPrepare.mockResolvedValue({
            data: { export_key: 'key123' }
        });
        render(YoutubeVisTab);
        await fireEvent.click(
            screen.getByTestId('submit-button-youtube-vis-instance-segmentations')
        );
        await waitFor(() => {
            expect(openSpy).toHaveBeenCalledWith(
                expect.stringContaining('/export/download/key123'),
                '_blank'
            );
        });
    });

    it('shows an error message when the API fails', async () => {
        mocks.exportCollectionYoutubeVisPrepare.mockRejectedValue(new Error('Network error'));
        render(YoutubeVisTab);
        await fireEvent.click(
            screen.getByTestId('submit-button-youtube-vis-instance-segmentations')
        );
        await waitFor(() => {
            expect(screen.getByText(/Export failed/)).toBeInTheDocument();
        });
    });
});
