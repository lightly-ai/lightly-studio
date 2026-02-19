import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import GroupsGrid from './GroupsGrid.svelte';
import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';

class MockResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
}

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

// Mock useGlobalStorage
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: vi.fn(() => ({
        sampleSize: {
            subscribe: (fn: (value: { width: number; height: number }) => void) => {
                fn({ width: 3, height: 3 });
                return {
                    unsubscribe: vi.fn()
                };
            }
        },
        getSelectedSampleIds: vi.fn(() => ({
            subscribe: (fn: (value: Set<string>) => void) => {
                fn(new Set());
                return {
                    unsubscribe: vi.fn()
                };
            }
        })),
        toggleSampleSelection: vi.fn(),
        getCollectionVersion: vi.fn(() => Promise.resolve('1'))
    }))
}));

// Mock LazyTrigger component
vi.mock('$lib/components/LazyTrigger', () => ({
    LazyTrigger: vi.fn()
}));

const createMockGroup = (overrides?: Partial<GroupView>): GroupView => ({
    sample_id: `sample-${Math.random()}`,
    sample: {
        sample_id: `sample-${Math.random()}`,
        collection_id: 'collection-123',
        file_name: 'test.jpg',
        file_path_abs: '/path/to/test.jpg',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
    },
    similarity_score: 0.95,
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
    },
    sample_count: 1,
    ...overrides
});

describe('GroupsGrid', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.stubGlobal('ResizeObserver', MockResizeObserver);

        // Mock scrollTo on HTMLElement
        Element.prototype.scrollTo = vi.fn();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('displays loading state with spinner when isLoading is true', () => {
        render(GroupsGrid, {
            props: {
                collectionId: 'collection-123',
                groups: [],
                isLoading: true,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        expect(screen.getByText('Loading groups...')).toBeInTheDocument();
    });

    it('displays empty state when isEmpty is true', () => {
        render(GroupsGrid, {
            props: {
                collectionId: 'collection-123',
                groups: [],
                isLoading: false,
                isEmpty: true,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        expect(screen.getByText('No groups found')).toBeInTheDocument();
        expect(screen.getByText("This collection doesn't contain any groups.")).toBeInTheDocument();
    });

    it('does not display empty state when groups are present', () => {
        const groups = [createMockGroup()];

        render(GroupsGrid, {
            props: {
                collectionId: 'collection-123',
                groups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        expect(screen.queryByText('No groups found')).not.toBeInTheDocument();
    });

    it('does not display loading state when not loading', () => {
        const groups = [createMockGroup()];

        render(GroupsGrid, {
            props: {
                collectionId: 'collection-123',
                groups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        expect(screen.queryByText('Loading groups...')).not.toBeInTheDocument();
    });
});
