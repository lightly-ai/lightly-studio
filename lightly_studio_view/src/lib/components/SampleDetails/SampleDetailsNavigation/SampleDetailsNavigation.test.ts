import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleDetailsNavigation from './SampleDetailsNavigation.svelte';

const { gotoMock, mockPage } = vi.hoisted(() => ({
    gotoMock: vi.fn(),
    mockPage: {
        data: {
            sampleIndex: 3,
            sampleAdjacents: {
                subscribe: (run: (value: unknown) => void) => {
                    run({
                        samplePrevious: {
                            sample_id: 'sample-2',
                            sample: { collection_id: 'collection-1' }
                        },
                        sampleNext: {
                            sample_id: 'sample-4',
                            sample: { collection_id: 'collection-1' }
                        }
                    });
                    return () => {};
                }
            }
        },
        params: {
            dataset_id: 'dataset-1',
            collection_type: 'images'
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

describe('SampleDetailsNavigation', () => {
    beforeEach(() => {
        gotoMock.mockReset();
    });

    it('navigates once when pressing ArrowRight', async () => {
        render(SampleDetailsNavigation);

        await fireEvent.keyDown(window, { key: 'ArrowRight' });

        expect(gotoMock).toHaveBeenCalledTimes(1);
        expect(gotoMock).toHaveBeenCalledWith(
            '/datasets/dataset-1/images/collection-1/samples/sample-4/4',
            { invalidateAll: true }
        );
    });
});
