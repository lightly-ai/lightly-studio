import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { writable, readonly } from 'svelte/store';
import { goto } from '$app/navigation';
import Page from './+page.svelte';
import { load } from './+page';
import type { PageData } from './$types';

const featureFlags = writable<string[]>([]);
let summaryData: { file_name: string; lidar_channels: []; camera_channels: [] } | undefined;
const adjacentSequences = vi.hoisted(() => ({
    data: undefined as
        | { previous_sample_id: string | null; next_sample_id: string | null }
        | undefined
}));

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$app/state', () => ({
    page: {
        url: new URL('http://localhost/datasets/dataset-1/mcap/collection-1/point-clouds/sequence-1'),
        params: { dataset_id: 'dataset-1' },
        state: {}
    }
}));

vi.mock('$lib/hooks/useAdjacentMcapSequences/useAdjacentMcapSequences', () => ({
    useAdjacentMcapSequences: () => ({ query: adjacentSequences, refetch: vi.fn() })
}));

vi.mock('$lib/hooks', () => ({
    useFeatureFlags: () => ({ featureFlags: readonly(featureFlags) }),
    // The workspace context fetches the sequence summary and tick details; stub them so no live query runs.
    useMcapSequenceSummary: () => ({
        summary: { data: summaryData, isLoading: false, isError: false },
        refetch: vi.fn()
    }),
    useMcapSequenceTicks: () => ({
        ticks: {
            data: {
                ticks: [
                    { seq_number: 0, timestamp_ns: 1000 },
                    { seq_number: 1, timestamp_ns: 2000 }
                ]
            }
        },
        refetch: vi.fn()
    }),
    useTickDetails: () => ({ tickDetails: { data: undefined } }),
    useCloudPointFrame: () => ({
        query: { data: undefined, isLoading: false, isError: false, refetch: vi.fn() }
    })
}));

const mockPageData = {
    datasetId: 'dataset-1',
    collectionId: 'collection-1',
    collectionName: 'Collection 1',
    collectionType: 'mcap',
    sequenceId: 'sequence-1'
} as unknown as PageData;

describe('[collection_type]/[collection_id]/point-clouds/[sequence_id] page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        summaryData = undefined;
        adjacentSequences.data = undefined;
    });

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

    it('shows the recording file name in the breadcrumb once the summary loads', async () => {
        featureFlags.set(['point_cloud_rendering']);
        summaryData = { file_name: 'drive_001.mcap', lidar_channels: [], camera_channels: [] };
        render(Page, { props: { data: mockPageData } });

        const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
        expect(breadcrumb).toHaveTextContent('drive_001.mcap');
    });

    it('falls back to the sequence id in the breadcrumb while the summary loads', async () => {
        featureFlags.set(['point_cloud_rendering']);
        render(Page, { props: { data: mockPageData } });

        const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
        expect(breadcrumb).toHaveTextContent('Point cloud sequence-1');
    });

    it('reflects timeline navigation in the one-based tick hash', async () => {
        featureFlags.set(['point_cloud_rendering']);
        const user = userEvent.setup();
        render(Page, { props: { data: mockPageData } });

        await user.click(await screen.findByRole('button', { name: 'Next frame' }));

        expect(goto).toHaveBeenCalledOnce();
        const [url, options] = vi.mocked(goto).mock.calls[0];
        expect(url).toBeInstanceOf(URL);
        expect((url as URL).hash).toBe('#tick=2');
        expect(options).toMatchObject({ replaceState: true, noScroll: true, keepFocus: true });
    });

    it('opens the next sequence from the timeline on its first tick', async () => {
        featureFlags.set(['point_cloud_rendering']);
        adjacentSequences.data = { previous_sample_id: null, next_sample_id: 'sequence-2' };
        const user = userEvent.setup();
        render(Page, {
            props: { data: mockPageData }
        });

        expect(await screen.findByRole('button', { name: 'Previous sequence' })).toBeDisabled();
        await user.click(screen.getByRole('button', { name: 'Next sequence' }));

        expect(goto).toHaveBeenCalledExactlyOnceWith(
            '/datasets/dataset-1/mcap/collection-1/point-clouds/sequence-2'
        );
    });

    it('opens the previous sequence from the timeline', async () => {
        featureFlags.set(['point_cloud_rendering']);
        adjacentSequences.data = { previous_sample_id: 'sequence-0', next_sample_id: null };
        const user = userEvent.setup();
        render(Page, { props: { data: mockPageData } });

        expect(await screen.findByRole('button', { name: 'Next sequence' })).toBeDisabled();
        await user.click(screen.getByRole('button', { name: 'Previous sequence' }));

        expect(goto).toHaveBeenCalledExactlyOnceWith(
            '/datasets/dataset-1/mcap/collection-1/point-clouds/sequence-0'
        );
    });
});

describe('point-cloud sequence page load', () => {
    // The route dataset slot carries a collection id; the dataset id comes from the loaded collection.
    const loadWith = (search: string, parentData: unknown): ReturnType<typeof load> =>
        load({
            params: {
                dataset_id: 'root-collection',
                collection_type: 'group',
                collection_id: 'group-collection',
                sequence_id: 'sequence'
            },
            url: new URL(
                `http://localhost/datasets/root-collection/group/group-collection/point-clouds/sequence${search}`
            ),
            parent: async () => parentData
        } as unknown as Parameters<typeof load>[0]);

    it('keeps a sequence collection as the breadcrumb target and derives the dataset id', async () => {
        const result = await loadWith('?group_id=group', {
            collection: {
                dataset_id: 'dataset',
                collection_id: 'sequence-collection',
                name: 'Sequences',
                sample_type: 'sequence',
                parent_collection_id: 'root-collection'
            },
            collectionHierarchy: []
        });

        expect(result).toEqual({
            datasetId: 'dataset',
            collectionName: 'Sequences',
            collectionType: 'sequence',
            collectionId: 'sequence-collection',
            sequenceId: 'sequence',
            groupId: 'group'
        });
    });

    it('points the breadcrumb at the parent sequence collection when reached from a group', async () => {
        const result = await loadWith('', {
            collection: {
                dataset_id: 'dataset',
                collection_id: 'group-collection',
                name: 'Group',
                sample_type: 'group',
                parent_collection_id: 'sequence-collection'
            },
            collectionHierarchy: [
                { collection_id: 'sequence-collection', name: 'Sequences', sample_type: 'sequence' }
            ]
        });

        expect(result).toEqual({
            datasetId: 'dataset',
            collectionName: 'Sequences',
            collectionType: 'sequence',
            collectionId: 'sequence-collection',
            sequenceId: 'sequence',
            groupId: undefined
        });
    });
});
