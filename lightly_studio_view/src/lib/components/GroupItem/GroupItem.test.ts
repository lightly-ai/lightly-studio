import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import GroupItem from './GroupItem.svelte';
import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';

// Mock the page store
vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-123'
        }
    }
}));

vi.mock('$app/navigation', () => ({
    goto: vi.fn()
}));

// Mock environment variables for Video and SampleImage components
vi.mock('$env/static/public', () => ({
    PUBLIC_VIDEOS_MEDIA_URL: '/api/videos',
    PUBLIC_VIDEOS_FRAMES_MEDIA_URL: '/api/video-frames',
    PUBLIC_SAMPLES_URL: '/api/images'
}));

const createMockGroup = (overrides?: Partial<GroupView>): GroupView => ({
    sample_id: 'sample-123',
    sample: {
        sample_id: 'sample-123',
        collection_id: 'collection-123',
        file_name: 'test.jpg',
        file_path_abs: '/path/to/test.jpg',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
    },
    similarity_score: 0.95,
    group_snapshot: null,
    sample_count: 1,
    ...overrides
});

describe('GroupItem', () => {
    it('renders image when group_snapshot is an image', () => {
        const group = createMockGroup({
            group_snapshot: {
                type: 'image',
                sample_id: 'image-123',
                file_name: 'image.jpg',
                file_path_abs: '/path/to/image.jpg',
                width: 1920,
                height: 1080,
                annotations: [],
                tags: [],
                sample: {
                    sample_id: 'image-123',
                    collection_id: 'collection-123',
                    file_name: 'image.jpg',
                    file_path_abs: '/path/to/image.jpg',
                    created_at: '2024-01-01T00:00:00Z',
                    updated_at: '2024-01-01T00:00:00Z'
                }
            }
        });

        const { container } = render(GroupItem, {
            props: {
                group,
                size: 200
            }
        });

        const image = container.querySelector('img.sample-image');
        expect(image).toBeInTheDocument();
        expect(image?.getAttribute('src')).toContain('sample/image-123');
    });

    it('renders video player when group_snapshot is a video', () => {
        const group = createMockGroup({
            group_snapshot: {
                type: 'video',
                sample_id: 'video-123',
                file_name: 'video.mp4',
                file_path_abs: '/path/to/video.mp4',
                width: 1920,
                height: 1080,
                duration_s: 10.5,
                fps: 30,
                sample: {
                    sample_id: 'video-123',
                    collection_id: 'collection-123',
                    file_name: 'video.mp4',
                    file_path_abs: '/path/to/video.mp4',
                    created_at: '2024-01-01T00:00:00Z',
                    updated_at: '2024-01-01T00:00:00Z'
                }
            }
        });

        const { container } = render(GroupItem, {
            props: {
                group,
                size: 200
            }
        });

        // Check for video element instead of img thumbnail
        const video = container.querySelector('video');
        expect(video).toBeInTheDocument();

        // Check for video indicator badge
        const videoIndicator = screen.getByText('Video');
        expect(videoIndicator).toBeInTheDocument();
    });

    it('renders "No preview" fallback when group_snapshot is null', () => {
        const group = createMockGroup({
            group_snapshot: null
        });

        render(GroupItem, {
            props: {
                group,
                size: 200
            }
        });

        const noPreview = screen.getByText('No preview');
        expect(noPreview).toBeInTheDocument();
    });

    it('displays similarity score when provided', () => {
        const group = createMockGroup({
            similarity_score: 0.87,
            group_snapshot: {
                type: 'image',
                sample_id: 'image-123',
                file_name: 'image.jpg',
                file_path_abs: '/path/to/image.jpg',
                width: 1920,
                height: 1080,
                annotations: [],
                tags: [],
                sample: {
                    sample_id: 'image-123',
                    collection_id: 'collection-123',
                    file_name: 'image.jpg',
                    file_path_abs: '/path/to/image.jpg',
                    created_at: '2024-01-01T00:00:00Z',
                    updated_at: '2024-01-01T00:00:00Z'
                }
            }
        });

        render(GroupItem, {
            props: {
                group,
                size: 200
            }
        });

        const similarityScore = screen.getByText('0.87');
        expect(similarityScore).toBeInTheDocument();
    });

    it('displays caption when showCaption is true and captions exist', () => {
        const group = createMockGroup({
            sample: {
                sample_id: 'sample-123',
                collection_id: 'collection-123',
                file_name: 'test.jpg',
                file_path_abs: '/path/to/test.jpg',
                created_at: '2024-01-01T00:00:00Z',
                updated_at: '2024-01-01T00:00:00Z',
                captions: [{ text: 'Test caption', source: 'user' }]
            },
            group_snapshot: {
                type: 'image',
                sample_id: 'image-123',
                file_name: 'image.jpg',
                file_path_abs: '/path/to/image.jpg',
                width: 1920,
                height: 1080,
                annotations: [],
                tags: [],
                sample: {
                    sample_id: 'image-123',
                    collection_id: 'collection-123',
                    file_name: 'image.jpg',
                    file_path_abs: '/path/to/image.jpg',
                    created_at: '2024-01-01T00:00:00Z',
                    updated_at: '2024-01-01T00:00:00Z'
                }
            }
        });

        render(GroupItem, {
            props: {
                group,
                size: 200,
                showCaption: true
            }
        });

        const caption = screen.getByText('Test caption');
        expect(caption).toBeInTheDocument();
    });

    it('does not display caption when showCaption is false', () => {
        const group = createMockGroup({
            sample: {
                sample_id: 'sample-123',
                collection_id: 'collection-123',
                file_name: 'test.jpg',
                file_path_abs: '/path/to/test.jpg',
                created_at: '2024-01-01T00:00:00Z',
                updated_at: '2024-01-01T00:00:00Z',
                captions: [{ text: 'Test caption', source: 'user' }]
            },
            group_snapshot: {
                type: 'image',
                sample_id: 'image-123',
                file_name: 'image.jpg',
                file_path_abs: '/path/to/image.jpg',
                width: 1920,
                height: 1080,
                annotations: [],
                tags: [],
                sample: {
                    sample_id: 'image-123',
                    collection_id: 'collection-123',
                    file_name: 'image.jpg',
                    file_path_abs: '/path/to/image.jpg',
                    created_at: '2024-01-01T00:00:00Z',
                    updated_at: '2024-01-01T00:00:00Z'
                }
            }
        });

        render(GroupItem, {
            props: {
                group,
                size: 200,
                showCaption: false
            }
        });

        const caption = screen.queryByText('Test caption');
        expect(caption).not.toBeInTheDocument();
    });

    it('displays sample count badge in bottom right corner', () => {
        const group = createMockGroup({
            sample_count: 5,
            group_snapshot: {
                type: 'image',
                sample_id: 'image-123',
                file_name: 'image.jpg',
                file_path_abs: '/path/to/image.jpg',
                width: 1920,
                height: 1080,
                annotations: [],
                tags: [],
                sample: {
                    sample_id: 'image-123',
                    collection_id: 'collection-123',
                    file_name: 'image.jpg',
                    file_path_abs: '/path/to/image.jpg',
                    created_at: '2024-01-01T00:00:00Z',
                    updated_at: '2024-01-01T00:00:00Z'
                }
            }
        });

        const { container } = render(GroupItem, {
            props: {
                group,
                size: 200
            }
        });

        // The badge shows "+4" which means there are 4 additional samples (5 total)
        const sampleCount = screen.getByText('+4');
        expect(sampleCount).toBeInTheDocument();

        // Find the badge div with title attribute
        const badge = container.querySelector('[title="5 samples in this group"]');
        expect(badge).toBeInTheDocument();
    });

    it('does not display sample count badge when count is 1', () => {
        const group = createMockGroup({
            sample_count: 1,
            group_snapshot: {
                type: 'image',
                sample_id: 'image-123',
                file_name: 'image.jpg',
                file_path_abs: '/path/to/image.jpg',
                width: 1920,
                height: 1080,
                annotations: [],
                tags: [],
                sample: {
                    sample_id: 'image-123',
                    collection_id: 'collection-123',
                    file_name: 'image.jpg',
                    file_path_abs: '/path/to/image.jpg',
                    created_at: '2024-01-01T00:00:00Z',
                    updated_at: '2024-01-01T00:00:00Z'
                }
            }
        });

        const { container } = render(GroupItem, {
            props: {
                group,
                size: 200
            }
        });

        // Badge should not be displayed when count is 1 (since the condition is > 1)
        const badge = container.querySelector('[title="1 sample in this group"]');
        expect(badge).not.toBeInTheDocument();
    });
});
