import { render } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import SampleDetailsAnnotation from './SampleDetailsAnnotation.svelte';

const annotation = {
    sample_id: 'annotation-1',
    annotation_type: 'segmentation_mask',
    annotation_label: { annotation_label_name: 'person' },
    segmentation_details: { x: 1, y: 2, width: 10, height: 12, segmentation_mask: [0, 4] }
};

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ segmentationMaskOpacity: writable(0.3) })
}));

vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({ annotation: { data: annotation }, updateAnnotation: vi.fn() })
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ setCurrentBoundingBox: vi.fn() })
}));

// The RLE rasterisation needs a real canvas; the opacity is all this test checks.
vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE',
    () => ({ default: () => ({ dataUrl: 'data:image/png;base64,', height: 12 }) })
);

describe('SampleDetailsAnnotation', () => {
    it('renders the mask with the stored mask opacity', () => {
        const { container } = render(SampleDetailsAnnotation, {
            props: {
                sampleId: 'sample-1',
                collectionId: 'collection-1',
                annotationId: 'annotation-1',
                sample: { width: 100, height: 100 },
                toggleAnnotationSelection: vi.fn(),
                scale: 1
            }
        });

        const opacity = Number(container.querySelector('image')?.getAttribute('opacity'));
        expect(opacity).toBeCloseTo(0.3);
    });
});
