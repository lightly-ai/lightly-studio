import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import VideoPreview from './VideoPreview.svelte';

describe('VideoPreview', () => {
    it('should render video element with correct src', () => {
        const { container } = render(VideoPreview, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video');
        expect(video).toBeTruthy();
        expect(video?.getAttribute('src')).toBe('test-video.mp4');
    });

    it('should render with preload metadata attribute', () => {
        const { container } = render(VideoPreview, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video');
        expect(video?.getAttribute('preload')).toBe('metadata');
    });

    it('should render video as muted', () => {
        const { container } = render(VideoPreview, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video') as HTMLVideoElement;
        expect(video?.muted).toBe(true);
    });

    it('should render play icon overlay', () => {
        const { container } = render(VideoPreview, { props: { src: 'test-video.mp4' } });
        const playIcon = container.querySelector('svg');
        expect(playIcon).toBeTruthy();
    });

    it('should apply custom className', () => {
        const { container } = render(VideoPreview, {
            props: { src: 'test-video.mp4', className: 'custom-class' }
        });
        const wrapper = container.querySelector('.custom-class');
        expect(wrapper).toBeTruthy();
    });

    it('should have aspect-square class by default', () => {
        const { container } = render(VideoPreview, { props: { src: 'test-video.mp4' } });
        const wrapper = container.querySelector('.aspect-square');
        expect(wrapper).toBeTruthy();
    });

    it('should apply additional videoProps', () => {
        const { container } = render(VideoPreview, {
            props: { src: 'test-video.mp4', videoProps: { loop: true } }
        });
        const video = container.querySelector('video');
        expect(video?.hasAttribute('loop')).toBe(true);
    });

    it('should render with rounded corners', () => {
        const { container } = render(VideoPreview, { props: { src: 'test-video.mp4' } });
        const video = container.querySelector('video');
        expect(video?.className).toContain('rounded-lg');
    });
});
