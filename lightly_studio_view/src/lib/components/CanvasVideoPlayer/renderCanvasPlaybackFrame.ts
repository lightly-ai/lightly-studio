import type { AnnotationView, FrameView, SampleView } from '$lib/api/lightly_studio_local';
import { getColorByLabel } from '$lib/utils';
import type { CustomColor } from '$lib/hooks/useCustomLabelColors';
import {
    computeStroke,
    drawBoxesOnContext,
    renderMasks,
    type BoundingBoxInput,
    type MaskInput
} from '$lib/workers/maskRendererUtils';

type CustomLabelColorMap = Record<string, CustomColor>;

export interface PlaybackAnnotationPayload {
    masks: MaskInput[];
    boxes: BoundingBoxInput[];
}

const parseCssColor = (color: string): [number, number, number, number] => {
    const normalized = color.trim();

    const rgbaMatch = normalized.match(
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

    if (normalized.startsWith('#')) {
        const hex = normalized.slice(1);
        if (hex.length === 3) {
            return [
                parseInt(`${hex[0]}${hex[0]}`, 16),
                parseInt(`${hex[1]}${hex[1]}`, 16),
                parseInt(`${hex[2]}${hex[2]}`, 16),
                255
            ];
        }
        if (hex.length === 6) {
            return [
                parseInt(hex.slice(0, 2), 16),
                parseInt(hex.slice(2, 4), 16),
                parseInt(hex.slice(4, 6), 16),
                255
            ];
        }
    }

    return [0, 0, 0, 255];
};

const clampAlpha = (value: number): number => Math.max(0, Math.min(value, 1));

const resolveLabelColor = (
    labelName: string,
    colorAlpha: number,
    customLabelColors: CustomLabelColorMap
): [number, number, number, number] => {
    const customColor = customLabelColors[labelName];
    if (!customColor) {
        return parseCssColor(getColorByLabel(labelName, colorAlpha).color);
    }

    const [r, g, b] = parseCssColor(customColor.color);
    const alphaValue = Math.round(clampAlpha(customColor.alpha * colorAlpha) * 255);
    return [r, g, b, alphaValue];
};

const normalizeRLE = (mask?: ArrayLike<number> | null): number[] => {
    if (!mask?.length) {
        return [];
    }

    return Array.from(mask, (value) => Number(value) || 0);
};

export function buildPlaybackAnnotationPayload({
    frame,
    showBoundingBoxesForSegmentation,
    customLabelColors
}: {
    frame: FrameView;
    showBoundingBoxesForSegmentation: boolean;
    customLabelColors: CustomLabelColorMap;
}): PlaybackAnnotationPayload {
    const sample = frame.sample as SampleView;
    const annotations: AnnotationView[] = sample.annotations ?? [];
    const masks: MaskInput[] = [];
    const boxes: BoundingBoxInput[] = [];

    for (const annotation of annotations) {
        const labelName = annotation.annotation_label?.annotation_label_name ?? 'label';

        if (
            annotation.annotation_type === 'instance_segmentation' &&
            annotation.segmentation_details
        ) {
            const rle = normalizeRLE(annotation.segmentation_details.segmentation_mask);
            if (rle.length) {
                masks.push({
                    rle,
                    color: resolveLabelColor(labelName, 0.4, customLabelColors)
                });
            }

            if (showBoundingBoxesForSegmentation) {
                const { x, y, width, height } = annotation.segmentation_details;
                boxes.push({
                    x: Math.round(x),
                    y: Math.round(y),
                    width: Math.round(width),
                    height: Math.round(height),
                    color: resolveLabelColor(labelName, 1, customLabelColors)
                });
            }

            continue;
        }

        if (
            annotation.annotation_type === 'object_detection' &&
            annotation.object_detection_details
        ) {
            const bbox = annotation.object_detection_details;
            boxes.push({
                x: Math.round(bbox.x),
                y: Math.round(bbox.y),
                width: Math.round(bbox.width),
                height: Math.round(bbox.height),
                color: resolveLabelColor(labelName, 1, customLabelColors)
            });
        }
    }

    return { masks, boxes };
}

export function renderCanvasPlaybackFrame({
    canvasCtx,
    maskCtx,
    maskCanvas,
    videoEl,
    sampleWidth,
    sampleHeight,
    payload,
    scaleX = 1,
    scaleY = 1
}: {
    canvasCtx: CanvasRenderingContext2D;
    maskCtx: CanvasRenderingContext2D;
    maskCanvas: HTMLCanvasElement;
    videoEl: HTMLVideoElement;
    sampleWidth: number;
    sampleHeight: number;
    payload: PlaybackAnnotationPayload;
    scaleX?: number;
    scaleY?: number;
}) {
    canvasCtx.clearRect(0, 0, sampleWidth, sampleHeight);
    canvasCtx.drawImage(videoEl, 0, 0, sampleWidth, sampleHeight);

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

    const stroke = computeStroke(scaleX, scaleY);
    drawBoxesOnContext(canvasCtx, payload.boxes, sampleWidth, sampleHeight, stroke);
}
