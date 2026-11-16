import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import WorkflowNavigation from './WorkflowNavigation.svelte';

const { gotoMock, mockPage } = vi.hoisted(() => ({
    gotoMock: vi.fn(),
    mockPage: {
        params: {
            dataset_id: 'dataset-1',
            collection_type: 'image',
            collection_id: 'collection-1',
            sampleId: 'sample-3'
        },
        url: new URL(
            'http://localhost/datasets/dataset-1/image/collection-1/images/sample-3?workflow_project=p1&workflow_batch=b1'
        )
    }
}));

vi.mock('$app/navigation', () => ({ goto: gotoMock, preloadData: vi.fn() }));
vi.mock('$app/state', () => ({ page: mockPage }));
vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ context: { isDrawing: false } })
}));

describe('WorkflowNavigation', () => {
    beforeEach(() => {
        gotoMock.mockReset();
    });

    it('moves to the neighbouring batch files and keeps the batch context', async () => {
        render(WorkflowNavigation, {
            props: { previousSampleId: 'sample-2', nextSampleId: 'sample-4' }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Next sample' }));
        await fireEvent.keyDown(window, { key: 'ArrowLeft' });

        expect(gotoMock).toHaveBeenNthCalledWith(
            1,
            '/datasets/dataset-1/image/collection-1/images/sample-4?workflow_project=p1&workflow_batch=b1'
        );
        expect(gotoMock).toHaveBeenNthCalledWith(
            2,
            '/datasets/dataset-1/image/collection-1/images/sample-2?workflow_project=p1&workflow_batch=b1'
        );
    });

    it('stops at the ends of the batch', () => {
        render(WorkflowNavigation, { props: { previousSampleId: null, nextSampleId: 'sample-4' } });

        expect(screen.queryByRole('button', { name: 'Previous sample' })).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Next sample' })).toBeInTheDocument();
    });
});
