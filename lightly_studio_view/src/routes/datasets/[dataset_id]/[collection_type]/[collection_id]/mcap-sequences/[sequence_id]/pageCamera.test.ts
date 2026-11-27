import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { goto } from '$app/navigation';
import Page from './+page.svelte';
import type { PageData } from './$types';

vi.mock('$app/navigation', () => ({ goto: vi.fn(), afterNavigate: vi.fn() }));
vi.mock('$app/state', () => ({
    page: {
        url: new URL('http://localhost/datasets/d/mcap/c/mcap-sequences/s#tick=2&camera=CAM_A'),
        params: { dataset_id: 'dataset-1' },
        state: {}
    },
    navigating: { type: null }
}));
vi.mock('$lib/hooks', () => ({
    useMcapSequenceSummary: () => ({ summary: { data: undefined } }),
    // Outside a batch: the page reads no batch file.
    useWorkflowFile: () => ({ query: { data: undefined, isError: false } }),
    useWorkflowFileTransition: () => ({ mutation: { mutateAsync: vi.fn(), isPending: false } })
}));
vi.mock('$lib/hooks/useAdjacentMcapSequences/useAdjacentMcapSequences', () => ({
    useAdjacentMcapSequences: () => ({ query: { data: undefined } })
}));
vi.mock(
    '$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte',
    async () => ({
        default: (await import('./WorkspaceStub.test.svelte')).default
    })
);

const data = {
    datasetId: 'dataset-1',
    annotationSourceCollectionId: 'group-1',
    collectionId: 'collection-1',
    collectionName: 'Collection 1',
    collectionType: 'mcap',
    sequenceId: 'sequence-1'
} as unknown as PageData;

describe('point-cloud sequence page hash state', () => {
    afterEach(() => vi.clearAllMocks());

    it('gives the tick and camera of the hash to the workspace and writes its changes', async () => {
        render(Page, { props: { data } });
        const hashState = screen.getByTestId('workspace-hash-state');
        expect(hashState).toHaveTextContent('tick 2, camera CAM_A');

        await fireEvent.click(screen.getByRole('button', { name: 'Go to tick 5' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Open CAM_B' }));

        expect(hashState).toHaveTextContent('tick 5, camera CAM_B');
        const writtenHashes = vi.mocked(goto).mock.calls.map(([url]) => (url as URL).hash);
        expect(writtenHashes).toEqual(['#tick=5&camera=CAM_A', '#tick=5&camera=CAM_B']);
    });
});
