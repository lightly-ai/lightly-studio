import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import VideoFrameDetails from './VideoFrameDetails.svelte';
import type { FrameView } from '$lib/api/lightly_studio_local';

describe('VideoFrameDetails', () => {
    const mockFrame: FrameView = {
        frame_number: 5,
        frame_timestamp_s: 0.167
    } as FrameView;

    const mockFrameURL = '/datasets/dataset-1/samples/frame-collection-1/frame-1';

    it('should render frame number', () => {
        const { getByTestId } = render(VideoFrameDetails, {
            props: { frame: mockFrame, frameURL: mockFrameURL }
        });

        const frameNumber = getByTestId('current-frame-number');
        expect(frameNumber.textContent).toBe('5');
    });

    it('should render frame timestamp with correct formatting', () => {
        const { getByTestId } = render(VideoFrameDetails, {
            props: { frame: mockFrame, frameURL: mockFrameURL }
        });

        const frameTimestamp = getByTestId('current-frame-timestamp');
        expect(frameTimestamp.textContent).toBe('0.167 s');
    });

    it('should render view frame button with correct href', () => {
        const { getByTestId } = render(VideoFrameDetails, {
            props: { frame: mockFrame, frameURL: mockFrameURL }
        });

        const viewButton = getByTestId('view-frame-button') as HTMLAnchorElement;
        expect(viewButton).toBeTruthy();
        expect(viewButton.getAttribute('href')).toBe(mockFrameURL);
    });

    it('should format timestamp to 3 decimal places', () => {
        const frameWithLongTimestamp: FrameView = {
            frame_number: 10,
            frame_timestamp_s: 1.23456789
        } as FrameView;

        const { getByTestId } = render(VideoFrameDetails, {
            props: { frame: frameWithLongTimestamp, frameURL: mockFrameURL }
        });

        const frameTimestamp = getByTestId('current-frame-timestamp');
        expect(frameTimestamp.textContent).toBe('1.235 s');
    });
});
