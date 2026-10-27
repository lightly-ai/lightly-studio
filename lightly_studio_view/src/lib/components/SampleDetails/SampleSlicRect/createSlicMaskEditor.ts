import {
    createMaskForLabels,
    getLabelAtPoint,
    getSegmentPixelIndexes,
    type Segmentation,
    type SuperpixelMaskEditor,
    type SuperpixelStrokePreview
} from '@lightly-ai/slic';
import {
    decodeRLEToBinaryMask,
    interpolateLineBetweenPoints
} from '$lib/components/SampleAnnotation/utils';

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
    const scaleX = width / segmentation.width;
    const scaleY = height / segmentation.height;
    let strokeMask: Uint8Array | null = null;
    let mode: SuperpixelStrokePreview['mode'] = 'add';
    const touchedLabels = new Set<number>();
    let lastPoint: { x: number; y: number } | null = null;
    const labelAtPoint = (point: { x: number; y: number }) =>
        getLabelAtPoint(segmentation, point.x, point.y, scaleX, scaleY);

    function* targetPixels(label: number): Generator<number> {
        for (const index of getSegmentPixelIndexes(segmentation, label)) {
            const x = index % segmentation.width;
            const y = Math.floor(index / segmentation.width);
            // Ceil matches nearest-neighbor upsampling: floor(target / scale).
            const left = Math.ceil(x * scaleX);
            const right = Math.ceil((x + 1) * scaleX);
            const bottom = Math.ceil((y + 1) * scaleY);
            for (let targetY = Math.ceil(y * scaleY); targetY < bottom; targetY++) {
                for (let targetX = left; targetX < right; targetX++) {
                    yield targetY * width + targetX;
                }
            }
        }
    }
    const paint = (point: { x: number; y: number }) => {
        const label = labelAtPoint(point);
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
            paint(point);
            lastPoint = point;
            return preview();
        },
        extendStroke(point) {
            if (!lastPoint) return null;
            const count = touchedLabels.size;
            for (const interpolated of interpolateLineBetweenPoints(lastPoint, point)) {
                paint(interpolated);
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
