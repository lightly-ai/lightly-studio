import { fireEvent, render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readable } from 'svelte/store';
import SampleDetailsNavigation from './SampleDetailsNavigation.svelte';

const { gotoMock, mockPage } = vi.hoisted(() => ({
    gotoMock: vi.fn(),
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
    goto: gotoMock
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
    useAdjacentImages: () => ({
        query: readable({
            data: {
                previous_sample_id: 'sample-2',
                next_sample_id: 'sample-4'
            }
        })
    })
}));

describe('SampleDetailsNavigation', () => {
    beforeEach(() => {
        gotoMock.mockReset();
    });

    it('navigates once when pressing ArrowRight', async () => {
        render(SampleDetailsNavigation);

        await fireEvent.keyDown(window, { key: 'ArrowRight' });

        expect(gotoMock).toHaveBeenCalledTimes(1);
        expect(gotoMock).toHaveBeenCalledWith(
            '/datasets/dataset-1/images/collection-1/samples/sample-4',
            { invalidateAll: true }
        );
    });
});
