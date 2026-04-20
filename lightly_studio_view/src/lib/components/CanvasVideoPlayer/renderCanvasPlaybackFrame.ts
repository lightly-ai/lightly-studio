import type { AnnotationView, FrameView, SampleView } from '$lib/api/lightly_studio_local';
import { getColorByLabel } from '$lib/utils';
import {
    computeStroke,
    drawBoxesOnContext,
    renderMasks,
    type BoundingBoxInput,
    type MaskInput
} from '$lib/workers/maskRendererUtils';

export interface PlaybackAnnotationPayload {
    masks: MaskInput[];
    boxes: BoundingBoxInput[];
}

const clampAlpha = (value: number): number => Math.max(0, Math.min(value, 1));

const parseCssColor = (color: string): [number, number, number, number] => {
    const rgbaMatch = color.match(
        /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)$/i
    );
    if (rgbaMatch) {
        const [, r, g, b, alpha] = rgbaMatch;
        return [
            Number(r),
            Number(g),
            Number(b),
            alpha == null ? 255 : Math.round(clampAlpha(Number(alpha)) * 255)
        ];
    }

    return [0, 0, 0, 255];
};

const resolveLabelColor = (labelName: string, alpha: number): [number, number, number, number] =>
    parseCssColor(getColorByLabel(labelName, alpha).color);

const normalizeRLE = (mask?: ArrayLike<number> | null): number[] => {
    if (!mask?.length) {
        return [];
    }

    return Array.from(mask, (value) => Number(value) || 0);
};

export function buildPlaybackAnnotationPayload({
    frame,
    showBoundingBoxesForSegmentation
}: {
    frame: FrameView | null;
    showBoundingBoxesForSegmentation: boolean;
}): PlaybackAnnotationPayload {
    if (!frame) {
        return { masks: [], boxes: [] };
    }

    const sample = frame.sample as SampleView;
    const annotations: AnnotationView[] = sample.annotations ?? [];
    const masks: MaskInput[] = [];
    const boxes: BoundingBoxInput[] = [];

    for (const annotation of annotations) {
        const labelName = annotation.annotation_label?.annotation_label_name;
        if (!labelName || annotation.annotation_type === 'classification') {
            continue;
        }

        if (
            annotation.annotation_type === 'instance_segmentation' &&
            annotation.segmentation_details
        ) {
            const rle = normalizeRLE(annotation.segmentation_details.segmentation_mask);
            if (rle.length) {
                masks.push({
                    rle,
                    color: resolveLabelColor(labelName, 0.4)
                });
            }

            if (showBoundingBoxesForSegmentation) {
                const { x, y, width, height } = annotation.segmentation_details;
                boxes.push({
                    x: Math.round(x),
                    y: Math.round(y),
                    width: Math.round(width),
                    height: Math.round(height),
                    color: resolveLabelColor(labelName, 1)
                });
            }

            continue;
        }

        if (
            annotation.annotation_type === 'object_detection' &&
            annotation.object_detection_details
        ) {
            const { x, y, width, height } = annotation.object_detection_details;
            boxes.push({
                x: Math.round(x),
                y: Math.round(y),
                width: Math.round(width),
                height: Math.round(height),
                color: resolveLabelColor(labelName, 1)
            });
        }
    }

    return { masks, boxes };
}

export function renderCanvasPlaybackFrame({
    canvasCtx,
    maskCtx,
    maskCanvas,
    mediaSource,
    sampleWidth,
    sampleHeight,
    payload,
    scaleX = 1,
    scaleY = 1
}: {
    canvasCtx: CanvasRenderingContext2D;
    maskCtx: CanvasRenderingContext2D;
    maskCanvas: HTMLCanvasElement;
    mediaSource: CanvasImageSource;
    sampleWidth: number;
    sampleHeight: number;
    payload: PlaybackAnnotationPayload;
    scaleX?: number;
    scaleY?: number;
}) {
    canvasCtx.clearRect(0, 0, sampleWidth, sampleHeight);
    canvasCtx.drawImage(mediaSource, 0, 0, sampleWidth, sampleHeight);

    maskCtx.clearRect(0, 0, sampleWidth, sampleHeight);
    if (payload.masks.length) {
        const pixelData = renderMasks(sampleWidth, sampleHeight, payload.masks);
        const imageData =
            typeof ImageData !== 'undefined'
                ? new ImageData(pixelData, sampleWidth, sampleHeight)
                : ({
                      data: pixelData,
                      width: sampleWidth,
                      height: sampleHeight
                  } as ImageData);
        maskCtx.putImageData(imageData, 0, 0);
        canvasCtx.drawImage(maskCanvas, 0, 0, sampleWidth, sampleHeight);
    }

    if (!payload.boxes.length) {
        return;
    }

    const stroke = computeStroke(scaleX, scaleY);
    drawBoxesOnContext(
        canvasCtx as unknown as OffscreenCanvasRenderingContext2D,
        payload.boxes,
        sampleWidth,
        sampleHeight,
        stroke
    );
}
