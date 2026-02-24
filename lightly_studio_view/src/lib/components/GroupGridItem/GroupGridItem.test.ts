import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import GroupGridItemTestWrapper from './GroupGridItemTestWrapper.test.svelte';
import type { ImageView, VideoView } from '$lib/api/lightly_studio_local/types.gen';

vi.mock('$env/static/public', () => ({
    PUBLIC_VIDEOS_MEDIA_URL: '/api/videos',
    PUBLIC_VIDEOS_FRAMES_MEDIA_URL: '/api/video-frames',
    PUBLIC_SAMPLES_URL: '/api/images',
    PUBLIC_LIGHTLY_STUDIO_API_URL: 'http://mock-url.com/api'
}));

describe('GroupGridItem', () => {
    const mockImageSample: ImageView = {
        type: 'image',
        file_name: 'test.jpg',
        file_path_abs: '/path/to/test.jpg',
        sample_id: 'sample-1'
    } as ImageView;

    const mockVideoSample: VideoView = {
        type: 'video',
        width: 1920,
        height: 1080,
        duration_s: 10.5,
        fps: 30,
        file_name: 'test.mp4',
        file_path_abs: '/path/to/test.mp4',
        sample_id: 'video-1',
        sample: {
            sample_id: 'video-1',
            collection_id: 'collection-1',
            created_at: new Date('2024-01-01'),
            updated_at: new Date('2024-01-01'),
            tags: [],
            captions: []
        }
    } as VideoView;

    it('renders with correct dimensions', () => {
        const { container } = render(GroupGridItemTestWrapper, {
            props: {
                sample: mockImageSample,
                width: 200,
                height: 200,
                sample_count: 1
            }
        });

        const wrapper = container.querySelector('div.relative');
        expect(wrapper).toBeInTheDocument();
        expect(wrapper).toHaveStyle({ width: '200px', height: '200px' });
    });

    it('renders image sample', () => {
        const { container } = render(GroupGridItemTestWrapper, {
            props: {
                sample: mockImageSample,
                width: 200,
                height: 200,
                sample_count: 1
            }
        });

        expect(container).toBeInTheDocument();
    });

    it('renders video sample', () => {
        const { container } = render(GroupGridItemTestWrapper, {
            props: {
                sample: mockVideoSample,
                width: 200,
                height: 200,
                sample_count: 1
            }
        });

        expect(container).toBeInTheDocument();
    });

    it('does not render count badge when sample_count is 1', () => {
        const { container } = render(GroupGridItemTestWrapper, {
            props: {
                sample: mockImageSample,
                width: 200,
                height: 200,
                sample_count: 1
            }
        });

        const badge = container.querySelector('.absolute.bottom-1.right-1');
        expect(badge).not.toBeInTheDocument();
    });

    it('renders count badge when sample_count is greater than 1', () => {
        const { container } = render(GroupGridItemTestWrapper, {
            props: {
                sample: mockImageSample,
                width: 200,
                height: 200,
                sample_count: 5
            }
        });

        const badge = container.querySelector('.absolute.bottom-1.right-1');
        expect(badge).toBeInTheDocument();
        expect(badge?.textContent).toBe('+4');
    });

    it('calculates count badge text correctly', () => {
        const { container } = render(GroupGridItemTestWrapper, {
            props: {
                sample: mockImageSample,
                width: 200,
                height: 200,
                sample_count: 10
            }
        });

        const badge = container.querySelector('.absolute.bottom-1.right-1');
        expect(badge?.textContent).toBe('+9');
    });

    it('renders with custom width and height', () => {
        const { container } = render(GroupGridItemTestWrapper, {
            props: {
                sample: mockImageSample,
                width: 400,
                height: 300,
                sample_count: 1
            }
        });

        const wrapper = container.querySelector('div.relative');
        expect(wrapper).toHaveStyle({ width: '400px', height: '300px' });
    });
});
