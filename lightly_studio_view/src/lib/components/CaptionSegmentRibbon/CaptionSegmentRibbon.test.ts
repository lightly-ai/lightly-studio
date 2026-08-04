import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CaptionSegmentRibbon from './CaptionSegmentRibbon.svelte';
import { captureVideoFrames } from './captureVideoFrames';

vi.mock('$env/static/public', () => ({
    PUBLIC_VIDEOS_MEDIA_URL: 'https://example.com/videos/media'
}));

vi.mock('./captureVideoFrames', () => ({
    captureVideoFrames: vi.fn()
}));

const captureVideoFramesMock = vi.mocked(captureVideoFrames);

// jsdom does not implement the object URL APIs used to hand thumbnails to <img>.
URL.createObjectURL = vi.fn();
URL.revokeObjectURL = vi.fn();

const defaultProps = {
    videoId: 'video-1',
    startTimeS: 10,
    endTimeS: 20
};

describe('CaptionSegmentRibbon', () => {
    beforeEach(() => {
        captureVideoFramesMock.mockReset();
    });

    afterEach(() => {
        cleanup();
    });

    it('requests ten uniform samples of the interval by default', async () => {
        captureVideoFramesMock.mockResolvedValue(undefined);

        render(CaptionSegmentRibbon, { props: defaultProps });

        await waitFor(() => expect(captureVideoFramesMock).toHaveBeenCalledTimes(1));
        const { timestampsS } = captureVideoFramesMock.mock.calls[0][0];
        expect(timestampsS).toHaveLength(10);
        expect(timestampsS[0]).toBe(10);
        expect(timestampsS[9]).toBe(20);
        expect(screen.getByText('0:10.0 – 0:20.0')).toBeInTheDocument();
    });

    it('renders a thumbnail per captured frame', async () => {
        captureVideoFramesMock.mockImplementation(async ({ timestampsS, onFrame }) => {
            timestampsS.forEach((_, index) => onFrame(index, `blob:frame-${index}`));
        });

        render(CaptionSegmentRibbon, { props: { ...defaultProps, sampleCount: 3 } });

        await waitFor(() => expect(screen.getAllByTestId('caption-segment-frame')).toHaveLength(3));
        expect(screen.getByAltText('Frame at 0:15.0')).toHaveAttribute('src', 'blob:frame-1');
    });

    it('reports when frames cannot be extracted', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        captureVideoFramesMock.mockRejectedValue(new Error('decode failed'));

        render(CaptionSegmentRibbon, { props: defaultProps });

        await waitFor(() => expect(screen.getByText('Preview unavailable')).toBeInTheDocument());
    });
});
