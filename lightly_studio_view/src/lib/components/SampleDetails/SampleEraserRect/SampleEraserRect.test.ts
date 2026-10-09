import { render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IMAGE_ADJUSTMENT_DEFAULTS, useGlobalStorage } from '$lib/hooks';
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
    const { segmentationMaskOpacity } = useGlobalStorage();

    afterEach(() => {
        segmentationMaskOpacity.set(IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity);
        vi.restoreAllMocks();
    });

    it('draws the eraser preview with the stored mask opacity', () => {
        // jsdom has no 2D canvas; the preview renderer skips drawing without one.
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
        segmentationMaskOpacity.set(0.3);

        const { container } = render(SampleEraserRect, {
            props: {
                sample: { width: 100, height: 100, annotations: [] },
                mousePosition: null,
                collectionId: 'collection-1',
                brushRadius: 5,
                drawerStrokeColor: 'rgb(0, 0, 255)',
                refetch: vi.fn()
            }
        });

        expect(container.querySelector('canvas')?.style.opacity).toBe('0.3');
    });
});
