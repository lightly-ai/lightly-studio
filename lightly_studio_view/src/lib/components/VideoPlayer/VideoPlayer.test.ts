import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import VideoPlayer from './VideoPlayer.svelte';

// Mock ResizeObserver (needed for bind:clientWidth and bind:clientHeight)
global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
};

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

    it('should toggle play/pause when spacebar is pressed while hovered', async () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video') as HTMLVideoElement;
        const wrapper = container.querySelector('div') as HTMLDivElement;

        // Mock play and pause methods
        video.play = vi.fn().mockResolvedValue(undefined);
        video.pause = vi.fn();

        // Initially paused
        Object.defineProperty(video, 'paused', {
            value: true,
            writable: true,
            configurable: true
        });

        // Hover over the player
        wrapper.dispatchEvent(new MouseEvent('mouseenter'));
        await new Promise((resolve) => setTimeout(resolve, 0));

        // Press spacebar - should play
        const spaceEvent = new KeyboardEvent('keydown', { code: 'Space' });
        const preventDefaultSpy = vi.spyOn(spaceEvent, 'preventDefault');
        window.dispatchEvent(spaceEvent);

        expect(preventDefaultSpy).toHaveBeenCalled();
        expect(video.play).toHaveBeenCalled();

        // Now playing
        Object.defineProperty(video, 'paused', {
            value: false,
            writable: true,
            configurable: true
        });

        // Press spacebar again - should pause
        const spaceEvent2 = new KeyboardEvent('keydown', { code: 'Space' });
        window.dispatchEvent(spaceEvent2);

        expect(video.pause).toHaveBeenCalled();
    });

    it('should ignore spacebar when typing in input', async () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video') as HTMLVideoElement;

        video.play = vi.fn().mockResolvedValue(undefined);
        Object.defineProperty(video, 'paused', { value: true, writable: true });

        // Create input element and dispatch event from it
        const input = document.createElement('input');
        document.body.appendChild(input);

        const spaceEvent = new KeyboardEvent('keydown', {
            code: 'Space',
            bubbles: true
        });
        Object.defineProperty(spaceEvent, 'target', {
            value: input,
            writable: false
        });

        window.dispatchEvent(spaceEvent);

        expect(video.play).not.toHaveBeenCalled();

        document.body.removeChild(input);
    });

    it('should ignore spacebar when typing in textarea', async () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video') as HTMLVideoElement;

        video.play = vi.fn().mockResolvedValue(undefined);
        Object.defineProperty(video, 'paused', { value: true, writable: true });

        // Create textarea element and dispatch event from it
        const textarea = document.createElement('textarea');
        document.body.appendChild(textarea);

        const spaceEvent = new KeyboardEvent('keydown', {
            code: 'Space',
            bubbles: true
        });
        Object.defineProperty(spaceEvent, 'target', {
            value: textarea,
            writable: false
        });

        window.dispatchEvent(spaceEvent);

        expect(video.play).not.toHaveBeenCalled();

        document.body.removeChild(textarea);
    });

    it('should only respond to spacebar when player is hovered', async () => {
        const { container } = render(VideoPlayer, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video') as HTMLVideoElement;
        const wrapper = container.querySelector('div') as HTMLDivElement;

        video.play = vi.fn().mockResolvedValue(undefined);
        video.pause = vi.fn();
        Object.defineProperty(video, 'paused', { value: true, writable: true });

        // Press spacebar without hovering - should not play
        const spaceEvent1 = new KeyboardEvent('keydown', { code: 'Space' });
        window.dispatchEvent(spaceEvent1);
        expect(video.play).not.toHaveBeenCalled();

        // Hover over the player
        wrapper.dispatchEvent(new MouseEvent('mouseenter'));
        await new Promise((resolve) => setTimeout(resolve, 0));

        // Press spacebar while hovering - should play
        const spaceEvent2 = new KeyboardEvent('keydown', { code: 'Space' });
        window.dispatchEvent(spaceEvent2);
        expect(video.play).toHaveBeenCalled();

        // Leave hover
        wrapper.dispatchEvent(new MouseEvent('mouseleave'));
        await new Promise((resolve) => setTimeout(resolve, 0));

        // Press spacebar after leaving - should not pause
        Object.defineProperty(video, 'paused', { value: false, writable: true });
        const spaceEvent3 = new KeyboardEvent('keydown', { code: 'Space' });
        window.dispatchEvent(spaceEvent3);
        expect(video.pause).not.toHaveBeenCalled();
    });
});
