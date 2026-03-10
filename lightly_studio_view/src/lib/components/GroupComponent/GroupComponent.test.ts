import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import GroupComponentTestWrapper from './GroupComponentTestWrapper.test.svelte';

describe('GroupComponent', () => {
    it('should render badge with title', () => {
        const { container } = render(GroupComponentTestWrapper, {
            props: { src: 'test.jpg', type: 'image', title: 'Test Title' }
        });
        const badge = container.querySelector('.badge');
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
});
