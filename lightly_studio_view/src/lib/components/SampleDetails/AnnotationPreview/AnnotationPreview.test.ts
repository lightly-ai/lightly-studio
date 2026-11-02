import { render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IMAGE_ADJUSTMENT_DEFAULTS } from '$lib/constants';
import { useGlobalStorage } from '$lib/hooks';
import AnnotationPreview from './AnnotationPreview.svelte';

vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/calculateBinaryMaskFromRLE',
    () => ({ default: () => ({ dataUrl: 'data:image/png;base64,', height: 3 }) })
);

const preview = {
    bbox: { x: 1, y: 1, width: 2, height: 2 },
    segmentation_mask: [10, 1, 1]
};

const renderInSvg = (saveAs: 'mask' | 'box') => {
    const { container } = render(AnnotationPreview, {
        props: { preview, image: { width: 4 }, saveAs },
        target: document.body.appendChild(
            document.createElementNS('http://www.w3.org/2000/svg', 'svg')
        )
    });
    return container;
};

describe('AnnotationPreview', () => {
    const { maskOpacity } = useGlobalStorage();

    afterEach(() => maskOpacity.set(IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity));

    it('renders the mask image and the box in mask mode', () => {
        const container = renderInSvg('mask');
        expect(container.querySelector('image')).not.toBeNull();
        expect(container.querySelector('rect')).not.toBeNull();
    });

    it('renders only the box in box mode', () => {
        const container = renderInSvg('box');
        expect(container.querySelector('image')).toBeNull();
        expect(container.querySelector('rect')).not.toBeNull();
    });

    it('keeps the mask visible when the mask opacity setting is 0', () => {
        maskOpacity.set(0);

        const container = renderInSvg('mask');

        expect(container.querySelector('image')?.getAttribute('opacity')).toBe('0.3');
    });
});
