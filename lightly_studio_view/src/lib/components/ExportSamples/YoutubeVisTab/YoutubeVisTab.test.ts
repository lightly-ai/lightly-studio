import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import type { VideoFilter } from '$lib/api/lightly_studio_local/types.gen';
import YoutubeVisTab from './YoutubeVisTab.svelte';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

const pageMock = vi.hoisted(() => ({ params: { collection_id: 'test-collection' } }));
vi.mock('$app/state', () => ({ page: pageMock }));

const mocks = vi.hoisted(() => ({
    exportCollectionYoutubeVisPrepare: vi.fn()
}));
vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionYoutubeVisPrepare: mocks.exportCollectionYoutubeVisPrepare
}));

vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: vi.fn()
}));

describe('YoutubeVisTab', () => {
    beforeEach(() => {
        mocks.exportCollectionYoutubeVisPrepare.mockReset();
        vi.mocked(useVideoFilters).mockReturnValue({
            videoFilter: writable(null),
            filterParams: writable(null),
            updateFilterParams: vi.fn(),
            updateSampleIds: vi.fn()
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('renders the description', () => {
        render(YoutubeVisTab);
        expect(screen.getByText(/YouTube-VIS format/)).toBeInTheDocument();
    });

    it('calls the API with null video_filter and opens the download tab when no filter is active', async () => {
        const openSpy = vi.spyOn(window, 'open').mockReturnValue(null);
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
        await waitFor(() => {
            expect(openSpy).toHaveBeenCalledWith(
                expect.stringContaining('/export/download/key123'),
                '_blank'
            );
        });
    });

    it('passes the active video filter to the API', async () => {
        vi.spyOn(window, 'open').mockReturnValue(null);
        mocks.exportCollectionYoutubeVisPrepare.mockResolvedValue({
            data: { export_key: 'key456' }
        });
        const activeFilter: VideoFilter = { filter_type: 'video', width: { min: 100 } };
        vi.mocked(useVideoFilters).mockReturnValueOnce({
            videoFilter: writable(activeFilter),
            filterParams: writable(null),
            updateFilterParams: vi.fn(),
            updateSampleIds: vi.fn()
        });
        render(YoutubeVisTab);
        await fireEvent.click(
            screen.getByTestId('submit-button-youtube-vis-instance-segmentations')
        );
        expect(mocks.exportCollectionYoutubeVisPrepare).toHaveBeenCalledWith({
            path: { collection_id: 'test-collection' },
            body: { video_filter: activeFilter }
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
