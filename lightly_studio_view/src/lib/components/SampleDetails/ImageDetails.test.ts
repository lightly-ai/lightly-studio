import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ImageDetails from './ImageDetails.svelte';
import { workflowFile } from '$lib/components/Workflow/workflowFile.fixture';
import type { Collection } from '$lib/services/types';

const SAMPLE_URL = 'http://localhost/datasets/dataset-1/image/collection-1/images/sample-3';
const BATCH_QUERY = '?workflow_project=project-1&workflow_batch=batch-1';

const pageState = vi.hoisted(() => ({
    url: new URL('http://localhost/'),
    state: {} as App.PageState
}));

vi.mock('$app/state', () => ({
    page: {
        get url() {
            return pageState.url;
        },
        get state() {
            return pageState.state;
        },
        params: {
            dataset_id: 'dataset-1',
            collection_type: 'image',
            collection_id: 'collection-1',
            sampleId: 'sample-3'
        }
    }
}));

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('./SampleDetailsPanel.svelte', async () => ({
    default: (await import('./SampleDetailsPanel.stub.svelte')).default
}));

vi.mock('$lib/hooks/useImage/useImage', () => ({
    useImage: () => ({
        image: { data: { sample: {}, width: 10, height: 10, annotations: [] } },
        refetch: vi.fn()
    })
}));

vi.mock('$lib/hooks/useAdjacentImages/useAdjacentImages', () => ({
    useAdjacentImages: () => ({ query: { data: undefined } })
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: { role: 'editor' } })
}));

vi.mock('$lib/hooks', () => ({
    useWorkflowFile: (getParams: () => unknown) => ({
        query: { data: getParams() ? workflowFile : undefined, isError: false }
    }),
    useWorkflowFileTransition: () => ({ mutation: { mutateAsync: vi.fn(), isPending: false } })
}));

const defaultProps = {
    sampleId: 'sample-3',
    collection: { collection_id: 'collection-1' } as Collection
};

describe('ImageDetails breadcrumb', () => {
    beforeEach(() => {
        pageState.state = {};
    });

    it('shows the batch path when opened from a batch link', () => {
        pageState.url = new URL(`${SAMPLE_URL}${BATCH_QUERY}`);
        render(ImageDetails, { props: defaultProps });

        const breadcrumb = screen.getByTestId('workflow-breadcrumb');
        expect(breadcrumb).toHaveTextContent('Roads');
        expect(breadcrumb).toHaveTextContent('Batch 1');
        expect(screen.queryByTestId('sample-details-breadcrumb')).not.toBeInTheDocument();
    });

    it('shows the dataset path when a batched sample is opened from the grid', () => {
        pageState.url = new URL(`${SAMPLE_URL}${BATCH_QUERY}`);
        pageState.state = { nav: 'dataset' };
        render(ImageDetails, { props: defaultProps });

        const breadcrumb = screen.getByTestId('sample-details-breadcrumb');
        expect(breadcrumb).toHaveTextContent('Root collection');
        expect(breadcrumb).toHaveTextContent('Samples');
        expect(screen.queryByTestId('workflow-breadcrumb')).not.toBeInTheDocument();
    });

    it('shows the dataset path outside a batch', () => {
        pageState.url = new URL(SAMPLE_URL);
        render(ImageDetails, { props: defaultProps });

        expect(screen.getByTestId('sample-details-breadcrumb')).toBeInTheDocument();
        expect(screen.queryByTestId('workflow-breadcrumb')).not.toBeInTheDocument();
    });
});
