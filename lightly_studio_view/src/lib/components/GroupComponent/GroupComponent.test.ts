import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import GroupComponentTestWrapper from './GroupComponentTestWrapper.test.svelte';

describe('GroupComponent', () => {
    it('should render badge with title', () => {
        const { container } = render(GroupComponentTestWrapper, {
            props: { src: 'test.jpg', type: 'image', title: 'Test Title' }
        });
        const badge = container.querySelector('.badge');
        expect(badge).toBeTruthy();
        expect(badge?.textContent).toBe('Test Title');
    });

    it('should render Image component when type is image', () => {
        const { container } = render(GroupComponentTestWrapper, {
            props: { src: 'test-image.jpg', type: 'image', title: 'Image' }
        });
        const img = container.querySelector('img');
        expect(img).toBeTruthy();
        expect(img?.getAttribute('src')).toBe('test-image.jpg');
    });

    it('should render VideoPreview component when type is video', () => {
        const { container } = render(GroupComponentTestWrapper, {
            props: { src: 'test-video.mp4', type: 'video', title: 'Video' }
        });
        const video = container.querySelector('video');
        expect(video).toBeTruthy();
    });

    it('should apply correct classes to Image component', () => {
        const { container } = render(GroupComponentTestWrapper, {
            props: { src: 'test.jpg', type: 'image', title: 'Test' }
        });
        const img = container.querySelector('img');
        expect(img?.className).toContain('w-60');
        expect(img?.className).toContain('h-60');
        expect(img?.className).toContain('object-contain');
    });

    it('should apply correct classes to VideoPreview component', () => {
        const { container } = render(GroupComponentTestWrapper, {
            props: { src: 'test.mp4', type: 'video', title: 'Test' }
        });
        const video = container.querySelector('video');
        expect(video?.className).toContain('w-60');
        expect(video?.className).toContain('h-60');
        expect(video?.className).toContain('object-contain');
    });

    it('should apply absolute positioning and margin to badge', () => {
        const { container } = render(GroupComponentTestWrapper, {
            props: { src: 'test.jpg', type: 'image', title: 'Badge Test' }
        });
        const badge = container.querySelector('.badge');
        expect(badge?.className).toContain('absolute');
        expect(badge?.className).toContain('m-2');
    });

    it('should use secondary variant for badge', () => {
        const { container } = render(GroupComponentTestWrapper, {
            props: { src: 'test.jpg', type: 'image', title: 'Badge Test' }
        });
        const badge = container.querySelector('.badge');
        expect(badge?.className).toContain('secondary');
    });
});
