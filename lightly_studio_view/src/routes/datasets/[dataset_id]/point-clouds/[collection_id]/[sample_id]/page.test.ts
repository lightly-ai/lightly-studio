import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import { writable, readonly } from 'svelte/store';
import Page from './+page.svelte';
import type { PageData } from './$types';

const featureFlags = writable<string[]>([]);
let ready = Promise.resolve();

vi.mock('$lib/hooks', () => ({
    useFeatureFlags: () => ({
        featureFlags: readonly(featureFlags),
        ready,
        error: writable(null)
    })
}));

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// This page reads frames through the query client; stub the hook so the test runs without a
// QueryClientProvider.
vi.mock(
    '$lib/components/PointCloudLabelingWorkspace/ProviderDiagnostics/useRecordingProbe.svelte',
    () => ({
        useRecordingProbe: () => ({
            phase: 'idle',
            telemetry: [],
            frameCount: 0,
            hasMore: false,
            position: 0,
            frame: undefined,
            isLoading: false,
            previous: vi.fn(),
            next: vi.fn()
        })
    })
);

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

        // The lazy chunk now pulls in the Three.js viewer, so importing it takes longer than
        // the default timeout allows.
        await waitFor(
            () => expect(screen.getByTestId('point-cloud-labeling-workspace')).toBeInTheDocument(),
            { timeout: 15000 }
        );
    });
});
