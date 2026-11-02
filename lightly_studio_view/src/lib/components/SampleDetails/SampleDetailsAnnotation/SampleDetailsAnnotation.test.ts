import { render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { IMAGE_ADJUSTMENT_DEFAULTS } from '$lib/constants';
import { useGlobalStorage } from '$lib/hooks';
import SampleDetailsAnnotation from './SampleDetailsAnnotation.svelte';

const predictionAnnotation = {
    sample_id: 'prediction',
    annotation_type: 'object_detection',
    annotation_collection_id: 'model',
    annotation_label: { annotation_label_name: 'hole' },
    confidence: 0.41,
    object_detection_details: { x: 1, y: 2, width: 15, height: 16 }
};

const maskAnnotation = {
    sample_id: 'mask',
    annotation_type: 'segmentation_mask',
    annotation_label: { annotation_label_name: 'person' },
    segmentation_details: { x: 1, y: 2, width: 10, height: 12, segmentation_mask: [0, 4] }
};

const mockAnnotation = vi.hoisted(() => ({ data: {} as Record<string, unknown> }));

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({
        showAnnotationTextLabelsStore: writable(false),
        showBoundingBoxesForSegmentationStore: writable(true)
    })
}));
vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ setCurrentBoundingBox: vi.fn() })
}));
vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({ annotation: mockAnnotation, updateAnnotation: vi.fn() })
}));
// The RLE rasterisation needs a real canvas; the mask tests only check the opacity.
vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE',
    () => ({ default: () => ({ dataUrl: 'data:image/png;base64,', height: 12 }) })
);

const defaultProps = {
    annotationId: 'prediction',
    sampleId: 'image',
    collectionId: 'images',
    sample: { width: 100, height: 100 },
    toggleAnnotationSelection: vi.fn(),
    scale: 1,
    showSourceLabels: true,
    colorBySource: false
};

describe('SampleDetailsAnnotation', () => {
    const { maskOpacity } = useGlobalStorage();

    beforeEach(() => {
        mockAnnotation.data = predictionAnnotation;
        // jsdom does not implement SVG text measurements used to size the annotation label.
        Object.defineProperty(SVGElement.prototype, 'getBBox', {
            configurable: true,
            value: () => ({ x: 0, y: 0, width: 30, height: 12 })
        });
    });
    afterEach(() => {
        Reflect.deleteProperty(SVGElement.prototype, 'getBBox');
        maskOpacity.set(IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity);
    });

    it('keeps prediction text when class coloring is chosen', async () => {
        const { rerender } = render(SampleDetailsAnnotation, defaultProps);
        expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('hole (0.41)');

        await rerender({ ...defaultProps, showSourceLabels: false });
        expect(screen.queryByTestId('svg-annotation-text')).not.toBeInTheDocument();
    });

    it('renders the mask with the stored mask opacity', () => {
        mockAnnotation.data = maskAnnotation;
        maskOpacity.set(0.3);

        const { container } = render(SampleDetailsAnnotation, {
            ...defaultProps,
            annotationId: 'mask'
        });

        const opacity = Number(container.querySelector('image')?.getAttribute('opacity'));
        expect(opacity).toBeCloseTo(0.3);
    });
});
