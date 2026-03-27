import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import Page from './+page.svelte';
import { writable, derived } from 'svelte/store';
import type { VideoView, CollectionView } from '$lib/api/lightly_studio_local/types.gen';
import { SampleType } from '$lib/api/lightly_studio_local';
import { useVideo, useCollectionWithChildren } from '$lib/hooks';
import type { PageData } from './$types';
import type { LayoutLoadResult } from '../../+layout';

vi.mock('$lib/hooks', () => ({
    useVideo: vi.fn(),
    useCollectionWithChildren: vi.fn()
}));

vi.mock('$lib/components', () => ({
    LayoutCard: vi.fn(() => ({ default: {} })),
    GroupsComponentsMenu: vi.fn(() => ({ default: {} })),
    VideoDetails: vi.fn(() => ({ default: {} })),
    Alert: vi.fn(() => ({ default: {} })),
    Spinner: vi.fn(() => ({ default: {} })),
    Separator: vi.fn(() => ({ default: {} }))
}));

vi.mock('$lib/components/VideoDetailsBreadcrumb/VideoDetailsBreadcrumb.svelte', () => ({
    default: {}
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
        globalStorage: mockGlobalStorage,
        selectedAnnotationFilterIds: derived(writable(new Set<string>()), ($set) =>
            Array.from($set)
        ),
        sampleSize: writable({ width: 256, height: 256 })
    };

    let useVideoMock: ReturnType<typeof vi.fn>;
    let useCollectionWithChildrenMock: ReturnType<typeof vi.fn>;

    beforeEach(async () => {
        vi.clearAllMocks();
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

        const { container } = render(Page, { props: { data: mockPageData } });

        // Since Spinner is mocked, we check that the video content is not rendered
        expect(container.querySelector('.flex.h-full.gap-4.px-4.pb-4')).toBeNull();
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

        // Since Alert is mocked, we verify the component would be rendered
        // by checking that the success path is not rendered
        const { container } = render(Page, { props: { data: mockPageData } });
        expect(container.querySelector('.flex.h-full.gap-4.px-4.pb-4')).toBeNull();
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

        const { container } = render(Page, { props: { data: groupPageData } });

        // Check for group layout structure
        expect(container.querySelector('.flex.h-full.gap-4.px-4.pb-4')).toBeTruthy();
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

        // Verify that useCollectionWithChildren was called with correct params
        expect(useCollectionWithChildrenMock).toHaveBeenCalledWith({
            collectionId: 'dataset-1'
        });
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

    it('should parse frameNumber from data when provided', () => {
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

        const pageDataWithFrame: PageData = {
            ...mockPageData,
            frameNumber: '42'
        };

        render(Page, { props: { data: pageDataWithFrame } });

        // Component should parse frameNumber to integer
        // Since VideoDetails is mocked, we just verify render doesn't throw
        expect(useVideoMock).toHaveBeenCalled();
    });

    it('should handle undefined frameNumber', () => {
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

        // Should not throw when frameNumber is undefined
        expect(useVideoMock).toHaveBeenCalled();
    });
});
