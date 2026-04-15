import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import Page from './+page.svelte';
import { writable } from 'svelte/store';
import type { VideoView, CollectionView } from '$lib/api/lightly_studio_local/types.gen';
import { SampleType } from '$lib/api/lightly_studio_local';
import { useVideo, useCollectionWithChildren } from '$lib/hooks';
import type { PageData } from './$types';
import type { LayoutLoadResult } from '../../+layout';

vi.mock('$lib/hooks', () => ({
    useVideo: vi.fn(),
    useCollectionWithChildren: vi.fn()
}));

// Track which components were rendered
let renderedComponents: string[] = [];

vi.mock('$lib/components', () => {
    const createMockComponent = (name: string) => {
        function MockComponent() {
            renderedComponents.push(name);
            // @ts-expect-error - Svelte component interface
            this.$set = () => {};
            // @ts-expect-error - Svelte component interface
            this.$on = () => {};
            // @ts-expect-error - Svelte component interface
            this.$destroy = () => {};
        }
        // Make function work with both `new` and direct calls
        MockComponent.prototype.constructor = MockComponent;
        return MockComponent;
    };

    return {
        LayoutCard: createMockComponent('LayoutCard'),
        GroupsComponentsMenu: createMockComponent('GroupsComponentsMenu'),
        VideoDetails: createMockComponent('VideoDetails'),
        Alert: createMockComponent('Alert'),
        Spinner: createMockComponent('Spinner'),
        Separator: createMockComponent('Separator')
    };
});

vi.mock('$lib/components/VideoDetailsBreadcrumb/VideoDetailsBreadcrumb.svelte', () => ({
    default: function MockVideoDetailsBreadcrumb() {
        renderedComponents.push('VideoDetailsBreadcrumb');
        // @ts-expect-error - Svelte component interface
        this.$set = () => {};
        // @ts-expect-error - Svelte component interface
        this.$on = () => {};
        // @ts-expect-error - Svelte component interface
        this.$destroy = () => {};
    }
}));

describe('Video Detail Page', () => {
    const mockVideoData: VideoView = {
        sample_id: 'video-1',
        file_name: 'test.mp4',
        width: 1920,
        height: 1080,
        duration_s: 10,
        fps: 30
    } as VideoView;

    const mockCollection: CollectionView = {
        collection_id: 'collection-1',
        name: 'Test Collection',
        parent_collection_id: null,
        sample_type: SampleType.VIDEO,
        created_at: new Date('2023-01-01'),
        updated_at: new Date('2023-01-02')
    } as CollectionView;

    const mockGlobalStorage = {
        reversibleActions: writable([]),
        sampleSize: writable({ width: 256, height: 256 })
    } as unknown as LayoutLoadResult['globalStorage'];

    const mockPageData: PageData = {
        params: {
            dataset_id: 'dataset-1',
            collection_type: 'image',
            collection_id: 'collection-1',
            sample_id: 'video-1'
        },
        frameNumber: undefined,
        groupId: undefined,
        collection: mockCollection as unknown as LayoutLoadResult['collection'],
        collectionHierarchy: [],
        globalStorage: mockGlobalStorage,
        sampleSize: writable({ width: 256, height: 256 })
    };

    let useVideoMock: ReturnType<typeof vi.fn>;
    let useCollectionWithChildrenMock: ReturnType<typeof vi.fn>;

    beforeEach(async () => {
        vi.clearAllMocks();
        renderedComponents = [];
        useVideoMock = vi.mocked(useVideo);
        useCollectionWithChildrenMock = vi.mocked(useCollectionWithChildren);
    });

    it('should show spinner when loading video', () => {
        useVideoMock.mockReturnValue({
            data: writable(undefined),
            error: writable(null),
            isLoading: writable(true),
            loadById: vi.fn(),
            refetch: writable(() => {})
        });

        useCollectionWithChildrenMock.mockReturnValue({
            collection: {
                data: writable(mockCollection)
            }
        } as ReturnType<typeof useCollectionWithChildrenMock>);

        render(Page, { props: { data: mockPageData } });

        // Verify Spinner is rendered
        expect(renderedComponents).toContain('Spinner');
        // Verify video content is not rendered
        expect(renderedComponents).not.toContain('VideoDetails');
        expect(renderedComponents).not.toContain('Alert');
    });

    it('should show error alert when video fails to load', () => {
        const mockError = new Error('Failed to load video');
        useVideoMock.mockReturnValue({
            data: writable(undefined),
            error: writable(mockError),
            isLoading: writable(false),
            loadById: vi.fn(),
            refetch: writable(() => {})
        });

        useCollectionWithChildrenMock.mockReturnValue({
            collection: {
                data: writable(mockCollection)
            }
        } as ReturnType<typeof useCollectionWithChildrenMock>);

        render(Page, { props: { data: mockPageData } });

        // Verify Alert is rendered
        expect(renderedComponents).toContain('Alert');
        // Verify video content is not rendered
        expect(renderedComponents).not.toContain('VideoDetails');
        expect(renderedComponents).not.toContain('Spinner');
    });

    it('should render group layout when collection_type is group and groupId is provided', () => {
        useVideoMock.mockReturnValue({
            data: writable(mockVideoData),
            error: writable(null),
            isLoading: writable(false),
            loadById: vi.fn(),
            refetch: writable(() => {})
        });

        useCollectionWithChildrenMock.mockReturnValue({
            collection: {
                data: writable(mockCollection)
            }
        } as ReturnType<typeof useCollectionWithChildrenMock>);

        const groupPageData: PageData = {
            ...mockPageData,
            params: {
                ...mockPageData.params,
                collection_type: 'group'
            },
            groupId: 'group-1'
        };

        render(Page, { props: { data: groupPageData } });

        // Verify group layout renders LayoutCard and VideoDetails
        // GroupsComponentsMenu is inside LayoutCard so won't be tracked by our mock
        expect(renderedComponents).toContain('LayoutCard');
        expect(renderedComponents).toContain('VideoDetails');
        // Verify error/loading states are not rendered
        expect(renderedComponents).not.toContain('Spinner');
        expect(renderedComponents).not.toContain('Alert');
    });

    it('should render standard layout when collection_type is not group', () => {
        useVideoMock.mockReturnValue({
            data: writable(mockVideoData),
            error: writable(null),
            isLoading: writable(false),
            loadById: vi.fn(),
            refetch: writable(() => {})
        });

        useCollectionWithChildrenMock.mockReturnValue({
            collection: {
                data: writable(mockCollection)
            }
        } as ReturnType<typeof useCollectionWithChildrenMock>);

        render(Page, { props: { data: mockPageData } });

        // Verify standard layout renders LayoutCard
        // VideoDetails and VideoDetailsBreadcrumb are inside LayoutCard so won't be tracked by our mock
        expect(renderedComponents).toContain('LayoutCard');
        // Verify error/loading states are not rendered
        expect(renderedComponents).not.toContain('Spinner');
        expect(renderedComponents).not.toContain('Alert');
    });

    it('should call loadById with correct sample_id when mounted', () => {
        const loadByIdMock = vi.fn();
        useVideoMock.mockReturnValue({
            data: writable(mockVideoData),
            error: writable(null),
            isLoading: writable(false),
            loadById: loadByIdMock,
            refetch: writable(() => {})
        });

        useCollectionWithChildrenMock.mockReturnValue({
            collection: {
                data: writable(mockCollection)
            }
        } as ReturnType<typeof useCollectionWithChildrenMock>);

        render(Page, { props: { data: mockPageData } });

        // The $effect should trigger loadById with the sample_id from params
        expect(loadByIdMock).toHaveBeenCalledWith('video-1');
    });
});
