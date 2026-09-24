import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import { writable, readonly } from 'svelte/store';
import Page from './+page.svelte';
import { load } from './+page';
import type { PageData } from './$types';

const featureFlags = writable<string[]>([]);

vi.mock('$lib/hooks', () => ({
    useFeatureFlags: () => ({ featureFlags: readonly(featureFlags) }),
    // The workspace context fetches the sequence summary and tick details; stub them so no live query runs.
    useMcapSequenceSummary: () => ({
        summary: { data: undefined, isLoading: false, isError: false },
        refetch: vi.fn()
    }),
    useTickDetails: () => ({ tickDetails: { data: undefined } })
}));

const mockPageData = {
    datasetId: 'dataset-1',
    collectionId: 'collection-1',
    sampleId: 'sample-1',
    sequenceId: 'sequence-1'
} as unknown as PageData;

describe('point-clouds/[collection_id]/[sample_id] page', () => {
    it('renders the route shell but not the workspace when the feature is disabled', () => {
        featureFlags.set([]);
        render(Page, { props: { data: mockPageData } });

        expect(screen.getByTestId('point-cloud-labeling-route')).toBeInTheDocument();
        expect(screen.queryByTestId('point-cloud-labeling-workspace')).not.toBeInTheDocument();
    });

    it('renders the workspace once the feature is enabled', async () => {
        featureFlags.set(['point_cloud_rendering']);
        render(Page, { props: { data: mockPageData } });

        await waitFor(() =>
            expect(screen.getByTestId('point-cloud-labeling-workspace')).toBeInTheDocument()
        );
    });
});

describe('point-cloud sample page load', () => {
    const loadWith = (search: string): ReturnType<typeof load> =>
        load({
            params: { dataset_id: 'dataset', collection_id: 'collection', sample_id: 'sample' },
            url: new URL(
                `http://localhost/datasets/dataset/point-clouds/collection/sample${search}`
            )
        } as Parameters<typeof load>[0]);

    it('maps route and query parameters to page data', async () => {
        const result = await loadWith('?collection_type=group&sequence_id=sequence&group_id=group');

        expect(result).toEqual({
            datasetId: 'dataset',
            collectionType: 'group',
            collectionId: 'collection',
            sampleId: 'sample',
            sequenceId: 'sequence',
            groupId: 'group'
        });
    });

    it('leaves optional query values undefined when absent but sequence_id is present', async () => {
        const result = await load({
            params: {
                dataset_id: 'dataset',
                collection_id: 'collection',
                sample_id: 'sample'
            },
            url: new URL(
                'http://localhost/datasets/dataset/point-clouds/collection/sample?sequence_id=sequence'
            )
        } as Parameters<typeof load>[0]);

        expect(result).toEqual({
            datasetId: 'dataset',
            collectionType: undefined,
            collectionId: 'collection',
            sampleId: 'sample',
            sequenceId: 'sequence',
            groupId: undefined
        });
    });

    it('raises a 400 when sequence_id is absent', async () => {
        await expect(loadWith('')).rejects.toMatchObject({ status: 400 });
    });
});
