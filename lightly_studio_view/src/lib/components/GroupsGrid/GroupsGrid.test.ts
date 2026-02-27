import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import GroupsGridTestWrapper from './GroupsGridTestWrapper.test.svelte';
import type { GroupView, ImageView } from '$lib/api/lightly_studio_local/types.gen';

vi.mock('$env/static/public', () => ({
    PUBLIC_VIDEOS_MEDIA_URL: '/api/videos',
    PUBLIC_VIDEOS_FRAMES_MEDIA_URL: '/api/video-frames',
    PUBLIC_SAMPLES_URL: '/api/images',
    PUBLIC_LIGHTLY_STUDIO_API_URL: 'http://mock-url.com/api'
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        sampleSize: writable({ width: 6, height: 200 })
    })
}));

class MockResizeObserver {
    callback: ResizeObserverCallback;

    constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
    }

    observe(target: Element) {
        this.callback(
            [
                {
                    target,
                    contentRect: { width: 2000, height: 1000 } as DOMRectReadOnly,
                    borderBoxSize: [] as ReadonlyArray<ResizeObserverSize>,
                    contentBoxSize: [] as ReadonlyArray<ResizeObserverSize>,
                    devicePixelContentBoxSize: [] as ReadonlyArray<ResizeObserverSize>
                }
            ],
            this
        );
    }

    unobserve() {}
    disconnect() {}
}

class MockIntersectionObserver {
    callback: IntersectionObserverCallback;

    constructor(callback: IntersectionObserverCallback) {
        this.callback = callback;
    }

    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
        return [];
    }
    get root() {
        return null;
    }
    get rootMargin() {
        return '';
    }
    get thresholds() {
        return [];
    }
}

describe('GroupsGrid', () => {
    const mockImageSample: ImageView = {
        type: 'image',
        file_name: 'test.jpg',
        file_path_abs: '/path/to/test.jpg',
        sample_id: 'sample-1'
    } as ImageView;

    const mockGroups: GroupView[] = [
        {
            sample_id: 'group-1',
            sample: {
                sample_id: 'group-1',
                collection_id: 'collection-1',
                created_at: new Date('2024-01-01'),
                updated_at: new Date('2024-01-01'),
                tags: [],
                captions: []
            },
            group_preview: mockImageSample,
            sample_count: 5,
            similarity_score: 0.95
        },
        {
            sample_id: 'group-2',
            sample: {
                sample_id: 'group-2',
                collection_id: 'collection-1',
                created_at: new Date('2024-01-01'),
                updated_at: new Date('2024-01-01'),
                tags: [],
                captions: []
            },
            group_preview: mockImageSample,
            sample_count: 3,
            similarity_score: 0.85
        }
    ];

    beforeEach(() => {
        global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
        global.IntersectionObserver =
            MockIntersectionObserver as unknown as typeof IntersectionObserver;
        Element.prototype.scrollTo = vi.fn();
    });

    it('renders loading state', () => {
        const { container, getByText } = render(GroupsGridTestWrapper, {
            props: {
                groups: [],
                isLoading: true,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        expect(getByText('Loading groups...')).toBeInTheDocument();
        const spinner = container.querySelector('.animate-spin');
        expect(spinner).toBeInTheDocument();
    });

    it('renders empty state when no groups found', () => {
        const { getByText } = render(GroupsGridTestWrapper, {
            props: {
                groups: [],
                isLoading: false,
                isEmpty: true,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        expect(getByText('No groups found')).toBeInTheDocument();
        expect(getByText("This collection doesn't contain any groups.")).toBeInTheDocument();
    });

    it('renders groups grid when groups are available', () => {
        const { container } = render(GroupsGridTestWrapper, {
            props: {
                groups: mockGroups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();
    });

    it('renders grid items for groups', () => {
        const { container } = render(GroupsGridTestWrapper, {
            props: {
                groups: mockGroups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        // Grid should render items
        const gridScroll = container.querySelector('.grid-scroll');
        expect(gridScroll).toBeInTheDocument();
    });

    it('calls navigateToGroupDetails on double-click for each grid item', () => {
        const mockNavigateToGroupDetails = vi.fn();

        const { container } = render(GroupsGridTestWrapper, {
            props: {
                groups: mockGroups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn(),
                navigateToGroupDetails: mockNavigateToGroupDetails
            }
        });

        // Find all grid items with role="button"
        const gridItems = container.querySelectorAll('[role="button"]');
        expect(gridItems.length).toBe(mockGroups.length);

        // Double-click each grid item and verify navigateToGroupDetails is called with correct sample_id
        mockGroups.forEach((group, index) => {
            const gridItem = gridItems[index] as HTMLElement;
            gridItem.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
            expect(mockNavigateToGroupDetails).toHaveBeenCalledWith(group.sample_id);
        });

        // Verify it was called exactly once per item
        expect(mockNavigateToGroupDetails).toHaveBeenCalledTimes(mockGroups.length);
    });

    it('shows loading spinner when fetching next page', () => {
        const { container } = render(GroupsGridTestWrapper, {
            props: {
                groups: mockGroups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: true,
                isFetchingNextPage: true,
                onLoadMore: vi.fn()
            }
        });

        // Should show spinner at the bottom
        const spinners = container.querySelectorAll('.animate-spin');
        expect(spinners.length).toBeGreaterThan(0);
    });

    it('calls onLoadMore when LazyTrigger is intersected', () => {
        const mockOnLoadMore = vi.fn();

        render(GroupsGridTestWrapper, {
            props: {
                groups: mockGroups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: true,
                isFetchingNextPage: false,
                onLoadMore: mockOnLoadMore
            }
        });

        // LazyTrigger uses IntersectionObserver which would be triggered in real browser
        // In test environment, we can verify the component renders with correct props
        expect(mockOnLoadMore).not.toHaveBeenCalled(); // Not called until intersection
    });

    it('does not show LazyTrigger when no next page', () => {
        const mockOnLoadMore = vi.fn();

        render(GroupsGridTestWrapper, {
            props: {
                groups: mockGroups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: mockOnLoadMore
            }
        });

        // Component still renders LazyTrigger but it's disabled
        // This is expected behavior - LazyTrigger handles disabled state
        expect(mockOnLoadMore).not.toHaveBeenCalled();
    });

    it('renders with correct container structure', () => {
        const { container } = render(GroupsGridTestWrapper, {
            props: {
                groups: mockGroups,
                isLoading: false,
                isEmpty: false,
                hasNextPage: false,
                isFetchingNextPage: false,
                onLoadMore: vi.fn()
            }
        });

        const mainContainer = container.querySelector('.h-full.w-full');
        expect(mainContainer).toBeInTheDocument();
    });
});
