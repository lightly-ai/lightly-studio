import { fireEvent, render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleDetailsNavigation from './SampleDetailsNavigation.svelte';

const { gotoMock, preloadDataMock, mockPage, adjacents } = vi.hoisted(() => ({
    gotoMock: vi.fn(),
    preloadDataMock: vi.fn(),
    adjacents: {
        data: {
            previous_sample_id: 'sample-2',
            next_sample_id: 'sample-4'
        } as Record<string, unknown>
    },
    mockPage: {
        params: {
            dataset_id: 'dataset-1',
            collection_type: 'images',
            collection_id: 'collection-1',
            sampleId: 'sample-3'
        }
    }
}));

vi.mock('$app/navigation', () => ({
    goto: gotoMock,
    preloadData: preloadDataMock
}));

vi.mock('$app/state', () => ({
    page: mockPage
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: { isDrawing: false }
    })
}));

vi.mock('$lib/hooks/useAdjacentImages/useAdjacentImages', () => ({
    useAdjacentImages: () => ({ query: adjacents })
}));

describe('SampleDetailsNavigation', () => {
    beforeEach(() => {
        gotoMock.mockReset();
        adjacents.data = { previous_sample_id: 'sample-2', next_sample_id: 'sample-4' };
    });

    it('navigates once when pressing ArrowRight', async () => {
        render(SampleDetailsNavigation);

        await fireEvent.keyDown(window, { key: 'ArrowRight' });

        expect(gotoMock).toHaveBeenCalledTimes(1);
        expect(gotoMock).toHaveBeenCalledWith(
            '/datasets/dataset-1/images/collection-1/images/sample-4',
            { state: { nav: 'dataset' } }
        );
    });

    it('opens a neighbour in a batch in workflow mode, in grid order', async () => {
        adjacents.data = {
            previous_sample_id: 'sample-2',
            next_sample_id: 'sample-4',
            previous_workflow: null,
            next_workflow: { project_id: 'p1', batch_id: 'b2', state: 'in_review' }
        };
        render(SampleDetailsNavigation);

        await fireEvent.keyDown(window, { key: 'ArrowRight' });
        await fireEvent.keyDown(window, { key: 'ArrowLeft' });

        expect(gotoMock).toHaveBeenNthCalledWith(
            1,
            '/datasets/dataset-1/images/collection-1/images/sample-4?workflow_project=p1&workflow_batch=b2',
            { state: { nav: 'dataset' } }
        );
        expect(gotoMock).toHaveBeenNthCalledWith(
            2,
            '/datasets/dataset-1/images/collection-1/images/sample-2',
            { state: { nav: 'dataset' } }
        );
    });
});
