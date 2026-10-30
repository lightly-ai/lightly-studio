import {
    createMaskForLabels,
    getLabelAtPoint,
    getSegmentPixelIndexes,
    type Segmentation,
    type SuperpixelMaskEditor,
    type SuperpixelStrokePreview
} from '@lightly-ai/slic';
import { decodeRLEToBinaryMask } from '$lib/components/SampleAnnotation/utils';
import { traceSlicStroke } from './traceSlicStroke';

interface SlicMaskEditorProps {
    segmentation: Segmentation;
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
    let mask = segmentationMask
        ? decodeRLEToBinaryMask(segmentationMask, width, height)
        : new Uint8Array(width * height);
    let strokeMask: Uint8Array | null = null;
    let mode: SuperpixelStrokePreview['mode'] = 'add';
    const touchedLabels = new Set<number>();
    let lastPoint: { x: number; y: number } | null = null;
    const toSlicPoint = (point: { x: number; y: number }) => ({
        x: Math.max(0, Math.min(segmentation.width, (point.x * segmentation.width) / width)),
        y: Math.max(0, Math.min(segmentation.height, (point.y * segmentation.height) / height))
    });
    const labelAtPoint = (point: { x: number; y: number }) => {
        const { x, y } = toSlicPoint(point);
        return getLabelAtPoint(segmentation, x, y);
    };

    function* targetPixels(label: number): Generator<number> {
        for (const index of getSegmentPixelIndexes(segmentation, label)) {
            const x = index % segmentation.width;
            const y = Math.floor(index / segmentation.width);
            // Multiply integer dimensions first to avoid rounding an exact edge into the next row.
            const left = Math.ceil((x * width) / segmentation.width);
            const right = Math.min(width, Math.ceil(((x + 1) * width) / segmentation.width));
            const bottom = Math.min(height, Math.ceil(((y + 1) * height) / segmentation.height));
            for (
                let targetY = Math.ceil((y * height) / segmentation.height);
                targetY < bottom;
                targetY++
            ) {
                for (let targetX = left; targetX < right; targetX++) {
                    yield targetY * width + targetX;
                }
            }
        }
    }
    const paint = (label: number) => {
        if (!strokeMask || touchedLabels.has(label)) return;
        touchedLabels.add(label);
        for (const index of targetPixels(label)) strokeMask[index] = mode === 'add' ? 1 : 0;
    };
    const preview = (): SuperpixelStrokePreview => ({
        mode,
        touchedLabels: Array.from(touchedLabels),
        // Include the existing annotation because its normal overlay is hidden while drawing.
        mask: strokeMask!
    });
    const cancelStroke = () => {
        strokeMask = null;
        lastPoint = null;
        touchedLabels.clear();
    };
    const editor: SuperpixelMaskEditor = {
        getMask: () => mask.slice(),
        getLabelAtPoint: labelAtPoint,
        getSegmentPreviewMask: (label) => createMaskForLabels(segmentation, [label]),
        beginStroke(point) {
            cancelStroke();
            mode = 'add';
            for (const index of targetPixels(labelAtPoint(point))) {
                if (mask[index]) {
                    mode = 'erase';
                    break;
                }
            }
            strokeMask = mask.slice();
            paint(labelAtPoint(point));
            lastPoint = point;
            return preview();
        },
        extendStroke(point) {
            if (!lastPoint) return null;
            const count = touchedLabels.size;
            for (const { x, y } of traceSlicStroke(toSlicPoint(lastPoint), toSlicPoint(point))) {
                paint(getLabelAtPoint(segmentation, x, y));
            }
            lastPoint = point;
            return touchedLabels.size === count ? null : preview();
        },
        commitStroke() {
            if (!strokeMask) return null;
            mask = strokeMask;
            cancelStroke();
            return mask.slice();
        },
        cancelStroke
    };
    return editor;
}
