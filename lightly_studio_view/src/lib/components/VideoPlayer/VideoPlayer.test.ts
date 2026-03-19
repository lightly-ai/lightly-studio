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

    it('should not show controls by default', () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video');
        expect(video?.hasAttribute('controls')).toBe(false);
    });

    it('should show controls when controls prop is true', () => {
        const { container } = render(VideoPlayer, {
            props: { src: 'test-video.mp4', videoProps: { controls: true } }
        });
        const video = container.querySelector('video');
        expect(video?.hasAttribute('controls')).toBe(true);
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
});
