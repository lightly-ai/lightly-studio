import { render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import SampleDetailsAnnotation from './SampleDetailsAnnotation.svelte';

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
    useAnnotation: () => ({
        annotation: {
            data: {
                sample_id: 'prediction',
                annotation_type: 'object_detection',
                annotation_collection_id: 'model',
                annotation_label: { annotation_label_name: 'hole' },
                confidence: 0.41,
                object_detection_details: { x: 1, y: 2, width: 15, height: 16 }
            }
        },
        updateAnnotation: vi.fn()
    })
}));
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
    beforeEach(() => {
        // jsdom does not implement SVG text measurements used to size the annotation label.
        Object.defineProperty(SVGElement.prototype, 'getBBox', {
            configurable: true,
            value: () => ({ x: 0, y: 0, width: 30, height: 12 })
        });
    });
    afterEach(() => Reflect.deleteProperty(SVGElement.prototype, 'getBBox'));

    it('keeps prediction text when class coloring is chosen', async () => {
        const { rerender } = render(SampleDetailsAnnotation, defaultProps);
        expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('hole (0.41)');

        await rerender({ ...defaultProps, showSourceLabels: false });
        expect(screen.queryByTestId('svg-annotation-text')).not.toBeInTheDocument();
    });
});
