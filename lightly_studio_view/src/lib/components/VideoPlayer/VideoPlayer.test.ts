import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import VideoPlayer from './VideoPlayer.svelte';

describe('VideoPlayer', () => {
    it('should render video element', () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video');
        expect(video).toBeTruthy();
    });

    it('should render video as muted by default', () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video') as HTMLVideoElement;
        expect(video?.muted).toBe(true);
    });

    it('should render with preload metadata attribute by default', () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video');
        expect(video?.getAttribute('preload')).toBe('metadata');
    });

    it('should not show native controls by default', () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video');
        expect(video?.hasAttribute('controls')).toBe(false);
    });

    it('should force native controls off even when videoProps requests them', () => {
        const { container } = render(VideoPlayer, {
            props: { src: 'test-video.mp4', videoProps: { controls: true } }
        });
        const video = container.querySelector('video');
        expect(video?.hasAttribute('controls')).toBe(false);
    });

    it('should apply custom className via videoProps', () => {
        const { container } = render(VideoPlayer, {
            props: { src: 'test-video.mp4', videoProps: { class: 'custom-video-class' } }
        });
        const video = container.querySelector('video');
        expect(video?.className).toContain('custom-video-class');
    });

    it('should have playsinline attribute by default', () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video');
        expect(video?.hasAttribute('playsinline')).toBe(true);
    });

    it('should display error message when video fails to load', async () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video') as HTMLVideoElement;

        // Wait for effect to run
        await new Promise((resolve) => setTimeout(resolve, 0));

        // Mock error
        Object.defineProperty(video, 'error', {
            value: { code: 2 },
            writable: true
        });

        video.dispatchEvent(new Event('error'));

        // Wait for state update
        await new Promise((resolve) => setTimeout(resolve, 0));

        const errorMessage = container.querySelector('[role="status"]');
        expect(errorMessage).toBeTruthy();
        expect(errorMessage?.textContent).toContain('Network error while loading the video.');
    });

    it('should clear error message when video loads successfully', async () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video') as HTMLVideoElement;

        // Wait for effect to run
        await new Promise((resolve) => setTimeout(resolve, 0));

        // Trigger error
        Object.defineProperty(video, 'error', {
            value: { code: 3 },
            writable: true
        });
        video.dispatchEvent(new Event('error'));

        // Wait for state update
        await new Promise((resolve) => setTimeout(resolve, 0));

        let errorMessage = container.querySelector('[role="status"]');
        expect(errorMessage).toBeTruthy();

        // Trigger loadeddata
        video.dispatchEvent(new Event('loadeddata'));

        // Wait for state update
        await new Promise((resolve) => setTimeout(resolve, 0));

        errorMessage = container.querySelector('[role="status"]');
        expect(errorMessage).toBeFalsy();
    });

    it('should support unmuted video', () => {
        const { container } = render(VideoPlayer, {
            props: { src: 'test-video.mp4', videoProps: { muted: false } }
        });
        const video = container.querySelector('video') as HTMLVideoElement;
        expect(video?.muted).toBe(false);
    });

    it('should support different preload options', () => {
        const { container } = render(VideoPlayer, {
            props: { src: 'test-video.mp4', videoProps: { preload: 'auto' } }
        });
        const video = container.querySelector('video');
        expect(video?.getAttribute('preload')).toBe('auto');
    });

    it('should render the custom control bar', () => {
        const { getByRole, getByLabelText } = render(VideoPlayer, {
            props: { src: 'test-video.mp4' }
        });
        expect(getByRole('slider')).toBeTruthy();
        expect(getByLabelText('Play')).toBeTruthy();
    });

    it('should not render an event bar when no events are given', () => {
        const { queryByTestId } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        expect(queryByTestId('video-event-timeline')).toBeFalsy();
    });

    it('should render an event bar in the controls when events are given', () => {
        const { getByTestId, getByText } = render(VideoPlayer, {
            props: {
                src: 'test-video.mp4',
                durationS: 10,
                events: [
                    {
                        id: 'e1',
                        annotationCollectionId: 'coll-1',
                        label: 'Jump',
                        startTimeS: 2,
                        endTimeS: 4,
                        color: 'rgba(10, 20, 30, 0.7)',
                        contrastColor: 'rgba(245, 235, 225, 0.7)'
                    }
                ]
            }
        });

        expect(getByTestId('video-event-timeline')).toBeTruthy();
        expect(getByText('Jump')).toBeTruthy();
    });

    it('shows the event bar with an add button in edit mode even without events', () => {
        const { getByTestId } = render(VideoPlayer, {
            props: {
                src: 'test-video.mp4',
                durationS: 10,
                editableEvents: true,
                onEventAdd: () => {}
            }
        });

        expect(getByTestId('video-event-timeline')).toBeTruthy();
        expect(getByTestId('add-event-button')).toBeTruthy();
    });
});
