import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import CollectionLayoutHeader from './CollectionLayoutHeader.svelte';
import '@testing-library/jest-dom';

// Mock the Header and MenuDialogHost components
vi.mock('$lib/components', () => ({
    Header: () => ({})
}));

vi.mock('$lib/components/Header/MenuDialogHost.svelte', () => ({
    default: () => ({})
}));

describe('CollectionLayoutHeader', () => {
    const mockCollection = {
        id: 'collection-123',
        name: 'Test Collection',
        datasetId: 'dataset-456',
        total_sample_count: 100
    };

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
            render(CollectionLayoutHeader, {
                props: {
                    collection: mockCollection,
                    routeType: mockRouteType,
                    hasEmbeddings: true
                }
            });
        }).not.toThrow();
    });

    it('accepts required props', () => {
        const { component } = render(CollectionLayoutHeader, {
            props: {
                collection: mockCollection,
                routeType: mockRouteType,
                hasEmbeddings: false
            }
        });

        expect(component).toBeTruthy();
    });
});
