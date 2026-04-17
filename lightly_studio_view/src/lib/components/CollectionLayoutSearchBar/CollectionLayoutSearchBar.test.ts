import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import CollectionLayoutSearchBar from './CollectionLayoutSearchBar.svelte';
import '@testing-library/jest-dom';

// Mock the CollectionSearchBar component
vi.mock('$lib/components', () => ({
    CollectionSearchBar: () => ({})
}));

describe('CollectionLayoutSearchBar', () => {
    const mockRouteType = {
        isSamples: true,
        isGroups: false,
        isGroupDetails: false,
        isAnnotations: false,
        isSampleDetails: false,
        isAnnotationDetails: false,
        isCaptions: false,
        isVideos: false,
        isVideoFrames: false,
        isVideoDetails: false,
        showLeftSidebar: true
    };

    const mockSearch = {
        query_text: '',
        submittedQueryText: '',
        activeImage: null,
        previewUrl: null,
        isUploading: false,
        dragOver: false,
        handleKeyDown: vi.fn(),
        handlePaste: vi.fn(),
        handleDragOver: vi.fn(),
        handleDragLeave: vi.fn(),
        handleDrop: vi.fn(),
        handleFileSelect: vi.fn(),
        clearImage: vi.fn(),
        clearSearch: vi.fn()
    };

    it('renders on samples route with embeddings', () => {
        expect(() => {
            render(CollectionLayoutSearchBar, {
                props: {
                    routeType: mockRouteType,
                    hasEmbeddings: true,
                    search: mockSearch
                }
            });
        }).not.toThrow();
    });

    it('renders on videos route with embeddings', () => {
        expect(() => {
            render(CollectionLayoutSearchBar, {
                props: {
                    routeType: { ...mockRouteType, isSamples: false, isVideos: true },
                    hasEmbeddings: true,
                    search: mockSearch
                }
            });
        }).not.toThrow();
    });

    it('does not render without embeddings', () => {
        const { container } = render(CollectionLayoutSearchBar, {
            props: {
                routeType: mockRouteType,
                hasEmbeddings: false,
                search: mockSearch
            }
        });

        // Should not render CollectionSearchBar when no embeddings
        expect(container.querySelector('*')).toBeNull();
    });

    it('does not render on annotations route', () => {
        const { container } = render(CollectionLayoutSearchBar, {
            props: {
                routeType: { ...mockRouteType, isSamples: false, isAnnotations: true },
                hasEmbeddings: true,
                search: mockSearch
            }
        });

        // Should not render CollectionSearchBar on annotation routes
        expect(container.querySelector('*')).toBeNull();
    });

    it('accepts search state props', () => {
        const customSearch = {
            ...mockSearch,
            query_text: 'test query',
            submittedQueryText: 'test query',
            activeImage: 'image-url',
            isUploading: true,
            dragOver: true
        };

        const { component } = render(CollectionLayoutSearchBar, {
            props: {
                routeType: mockRouteType,
                hasEmbeddings: true,
                search: customSearch
            }
        });

        expect(component).toBeTruthy();
    });
});
