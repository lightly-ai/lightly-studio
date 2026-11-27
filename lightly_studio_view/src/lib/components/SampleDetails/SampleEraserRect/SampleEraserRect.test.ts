import { render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SampleEraserRect from './SampleEraserRect.svelte';

vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'dataset-1' } } }));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: { annotationId: null, isDrawing: false },
        setIsDrawing: vi.fn(),
        setAnnotationId: vi.fn()
    })
}));

vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({ updateAnnotation: vi.fn() })
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [] })
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: [] })
}));

vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({ createAnnotation: vi.fn() })
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({ deleteAnnotation: vi.fn() })
}));

vi.mock('$lib/hooks/useAnnotationDeleteNavigation/useAnnotationDeleteNavigation', () => ({
    useAnnotationDeleteNavigation: () => ({})
}));

vi.mock('$lib/hooks/useSegmentationMaskEraser', () => ({
    useSegmentationMaskEraser: () => ({})
}));

describe('SampleEraserRect', () => {
    afterEach(() => vi.restoreAllMocks());

    it('draws the eraser preview with the given opacity', () => {
        // jsdom has no 2D canvas; the preview renderer skips drawing without one.
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);

        const { container } = render(SampleEraserRect, {
            props: {
                sample: { width: 100, height: 100, annotations: [] },
                mousePosition: null,
                collectionId: 'collection-1',
                brushSize: 10,
                drawerStrokeColor: 'rgb(0, 0, 255)',
                previewOpacity: 0.3,
                refetch: vi.fn()
            }
        });

        expect(container.querySelector('foreignObject')?.getAttribute('opacity')).toBe('0.3');
    });

    it('outlines the exact pixels the eraser paints under the cursor', () => {
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);

        const { container } = render(SampleEraserRect, {
            props: {
                sample: { width: 100, height: 100, annotations: [] },
                mousePosition: { x: 3.7, y: 5.2 },
                collectionId: 'collection-1',
                brushSize: 2,
                drawerStrokeColor: 'rgb(0, 0, 255)',
                previewOpacity: 0.3,
                refetch: vi.fn()
            }
        });

        expect(container.querySelector('path')?.getAttribute('d')).toBe('M3 4H5V5H5V6H3V5H3V4Z');
    });

    it('shows a circle around the eraser pixels for a size above 3', () => {
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);

        const { container } = render(SampleEraserRect, {
            props: {
                sample: { width: 100, height: 100, annotations: [] },
                mousePosition: { x: 10.4, y: 19.6 },
                collectionId: 'collection-1',
                brushSize: 4,
                drawerStrokeColor: 'rgb(0, 0, 255)',
                previewOpacity: 0.3,
                refetch: vi.fn()
            }
        });

        const circle = container.querySelector('circle');
        expect([
            circle?.getAttribute('cx'),
            circle?.getAttribute('cy'),
            circle?.getAttribute('r')
        ]).toEqual(['10', '20', '2']);
    });
});
