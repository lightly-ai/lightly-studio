import { createSuperpixelMaskEditor } from '@lightly-ai/slic';
import { decodeRLEToBinaryMask } from '$lib/components/SampleAnnotation/utils';

interface SlicMaskEditorProps {
    segmentation: Parameters<typeof createSuperpixelMaskEditor>[0]['segmentation'];
    width: number;
    height: number;
    segmentationMask?: number[] | null;
}

export function createSlicMaskEditor({
    segmentation,
    width,
    height,
    segmentationMask
}: SlicMaskEditorProps) {
    const mask = segmentationMask
        ? decodeRLEToBinaryMask(segmentationMask, width, height)
        : new Uint8Array(width * height);
    return createSuperpixelMaskEditor({
        segmentation,
        mask,
        targetWidth: width,
        targetHeight: height,
        // Superpixels may be computed on a smaller image than the saved annotation.
        scaleX: width / segmentation.width,
        scaleY: height / segmentation.height
    });
}
