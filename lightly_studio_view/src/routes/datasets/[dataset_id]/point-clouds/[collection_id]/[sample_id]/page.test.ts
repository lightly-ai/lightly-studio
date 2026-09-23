import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import { writable, readonly } from 'svelte/store';
import Page from './+page.svelte';
import { load } from './+page';
import type { PageData } from './$types';

const featureFlags = writable<string[]>([]);
let ready = Promise.resolve();

vi.mock('$lib/hooks', () => ({
    useFeatureFlags: () => ({
        featureFlags: readonly(featureFlags),
        ready,
        error: writable(null)
    }),
    // The lazily-loaded workspace mounts the camera projection strip, which reads
    // the tick details query; stub it so no live query runs during the route test.
    useTickDetails: () => ({ tickDetails: { data: undefined } })
}));

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// This page reads datasetId/collectionId/sampleId from path params and
// collectionType/groupId from query params; the rest of PageData comes from parent layout loads.
const mockPageData = {
    datasetId: 'dataset-1',
    collectionId: 'collection-1',
    sampleId: 'sample-1',
    collectionType: 'mcap',
    groupId: undefined
} as unknown as PageData;

describe('point-clouds/[collection_id]/[sample_id] page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        featureFlags.set([]);
        ready = Promise.resolve();
    });

    it('shows a loading state before the feature flags resolve', () => {
        ready = new Promise(() => {
            // Intentionally never resolves for this assertion.
        });
        render(Page, { props: { data: mockPageData } });

        expect(screen.getByTestId('workspace-status-panel')).toHaveAttribute(
            'data-status',
            'loading'
        );
    });

    it('shows the unsupported state when the feature is disabled', async () => {
        render(Page, { props: { data: mockPageData } });

        await waitFor(() =>
            expect(screen.getByTestId('workspace-status-panel')).toHaveAttribute(
                'data-status',
                'unsupported'
            )
        );
    });

    it('lazy-loads and renders the workspace once the feature is enabled', async () => {
        featureFlags.set(['point_cloud_rendering']);
        render(Page, { props: { data: mockPageData } });

        await waitFor(() =>
            expect(screen.getByTestId('point-cloud-labeling-workspace')).toBeInTheDocument()
        );
    });
});

describe('point-cloud sample page load', () => {
    it('maps route and query parameters to page data', async () => {
        const result = await load({
            params: {
                dataset_id: 'dataset',
                collection_id: 'collection',
                sample_id: 'sample'
            },
            url: new URL(
                'http://localhost/datasets/dataset/point-clouds/collection/sample?collection_type=group&sequence_id=sequence&group_id=group'
            )
        } as Parameters<typeof load>[0]);

        expect(result).toEqual({
            datasetId: 'dataset',
            collectionType: 'group',
            collectionId: 'collection',
            sampleId: 'sample',
            sequenceId: 'sequence',
            groupId: 'group'
        });
    });

    it('leaves optional query values undefined when absent', async () => {
        const result = await load({
            params: {
                dataset_id: 'dataset',
                collection_id: 'collection',
                sample_id: 'sample'
            },
            url: new URL('http://localhost/datasets/dataset/point-clouds/collection/sample')
        } as Parameters<typeof load>[0]);

        expect(result).toEqual({
            datasetId: 'dataset',
            collectionType: undefined,
            collectionId: 'collection',
            sampleId: 'sample',
            sequenceId: undefined,
            groupId: undefined
        });
    });
});
