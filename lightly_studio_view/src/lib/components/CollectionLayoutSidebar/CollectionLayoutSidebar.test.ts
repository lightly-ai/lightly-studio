import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import CollectionLayoutSidebar from './CollectionLayoutSidebar.svelte';
import '@testing-library/jest-dom';

// Mock required components
vi.mock('$lib/components', () => ({
    LabelsMenu: () => ({}),
    TagsMenu: () => ({}),
    CombinedMetadataDimensionsFilters: () => ({})
}));

vi.mock('$lib/components/Segment/Segment.svelte', () => ({
    default: () => ({})
}));

describe('CollectionLayoutSidebar', () => {
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

    it('renders without crashing', () => {
        expect(() => {
            render(CollectionLayoutSidebar, {
                props: {
                    collectionId: 'collection-123',
                    gridType: 'samples',
                    routeType: mockRouteType,
                    annotationFilterRows: writable([]),
                    toggleAnnotationFilterSelection: vi.fn()
                }
            });
        }).not.toThrow();
    });

    it('accepts required props', () => {
        const mockAnnotationFilterRows = writable([
            { label_name: 'Car', total_count: 10, current_count: 5, selected: false },
            { label_name: 'Person', total_count: 20, current_count: 15, selected: true }
        ]);

        const toggleFn = vi.fn();

        const { component } = render(CollectionLayoutSidebar, {
            props: {
                collectionId: 'collection-456',
                gridType: 'annotations',
                routeType: mockRouteType,
                annotationFilterRows: mockAnnotationFilterRows,
                toggleAnnotationFilterSelection: toggleFn
            }
        });

        expect(component).toBeTruthy();
    });

    it('handles different grid types', () => {
        const gridTypes: Array<
            'samples' | 'annotations' | 'videos' | 'video_frames' | 'captions' | 'groups'
        > = ['samples', 'annotations', 'videos', 'video_frames', 'captions', 'groups'];

        gridTypes.forEach((gridType) => {
            expect(() => {
                render(CollectionLayoutSidebar, {
                    props: {
                        collectionId: 'collection-123',
                        gridType,
                        routeType: mockRouteType,
                        annotationFilterRows: writable([]),
                        toggleAnnotationFilterSelection: vi.fn()
                    }
                });
            }).not.toThrow();
        });
    });
});
