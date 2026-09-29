import { expect, it, vi } from 'vitest';
import { createSuperpixelMaskEditor } from '@lightly-ai/slic';
import { maskToDataUrl } from '$lib/components/SampleAnnotation/utils';
import { useSlicPreview } from './useSlicPreview.svelte';

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    maskToDataUrl: vi.fn((mask: Uint8Array) => `data:image/png;base64,${mask.join('')}`)
}));

vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor',
    () => ({ default: () => ({ r: 0, g: 0, b: 255, a: 255 }) })
);

it('renders hover and stroke masks independently and clears previews between strokes', () => {
    const editor = createSuperpixelMaskEditor({
        segmentation: {
            width: 2,
            height: 1,
            labels: new Int32Array([0, 1]),
            boundaries: new Uint8Array([1, 1]),
            segmentCount: 2,
            labelPixelIndexes: [[0], [1]],
            pixelIndexes: new Uint32Array([0, 1]),
            segmentOffsets: new Uint32Array([0, 1, 2])
        },
        mask: new Uint8Array(2),
        targetWidth: 2,
        targetHeight: 1,
        scaleX: 1,
        scaleY: 1
    });
    const preview = useSlicPreview(() => ({ width: 2, height: 1, color: 'rgb(0, 0, 255)' }));
    preview.updateHover({ x: 0, y: 0 }, editor);
    expect(preview.hoverMaskDataUrl).toBe('data:image/png;base64,10');
    expect(maskToDataUrl).toHaveBeenLastCalledWith(new Uint8Array([1, 0]), 2, 1, {
        r: 0,
        g: 0,
        b: 255,
        a: 85
    });
    preview.updateHover({ x: 0, y: 0 }, editor);
    expect(maskToDataUrl).toHaveBeenCalledOnce();
    preview.renderStroke(new Uint8Array([1, 1]));
    expect(preview.strokeMaskDataUrl).toBe('data:image/png;base64,11');
    preview.clearStroke();
    expect(preview.strokeMaskDataUrl).toBe('');
    expect(preview.hoverMaskDataUrl).toBe('data:image/png;base64,10');
    preview.clear();
    expect(preview.hoverMaskDataUrl).toBe('');
    preview.updateHover({ x: 0, y: 0 }, editor);
    expect(preview.hoverMaskDataUrl).toBe('data:image/png;base64,10');
});
