import {
    AnnotationType,
    type AnnotationCreateInput,
    type AnnotationPreview
} from '$lib/api/lightly_studio_local';
import {
    decodeRLEToBinaryMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';

export type OutputType = 'mask' | 'box';
export type NormalizedPoint = { x: number; y: number };
export type NormalizedBox = { x: number; y: number; width: number; height: number };

// Drags shorter than this fraction of the image count as clicks.
const MIN_DRAG_SIZE = 0.005;

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));

export const normalizedPointFromEvent = (
    event: { clientX: number; clientY: number },
    rect: { left: number; top: number; width: number; height: number }
): NormalizedPoint => ({
    x: clamp01((event.clientX - rect.left) / rect.width),
    y: clamp01((event.clientY - rect.top) / rect.height)
});

export const boxFromPoints = (start: NormalizedPoint, end: NormalizedPoint): NormalizedBox => ({
    x: Math.min(start.x, end.x),
    y: Math.min(start.y, end.y),
    width: Math.abs(end.x - start.x),
    height: Math.abs(end.y - start.y)
});

export const isDragBox = (box: NormalizedBox): boolean =>
    box.width > MIN_DRAG_SIZE && box.height > MIN_DRAG_SIZE;

// Pastes the bbox-cropped preview RLE into a full-image mask, the format the create
// endpoint expects.
export const previewToFullImageRLE = (
    preview: Pick<AnnotationPreview, 'bbox' | 'segmentation_mask'>,
    image: { width: number; height: number }
): number[] => {
    const { bbox } = preview;
    const cropped = decodeRLEToBinaryMask(preview.segmentation_mask, bbox.width, bbox.height);
    const full = new Uint8Array(image.width * image.height);
    for (let y = 0; y < bbox.height; y += 1) {
        const targetY = bbox.y + y;
        if (targetY < 0 || targetY >= image.height) continue;
        for (let x = 0; x < bbox.width; x += 1) {
            const targetX = bbox.x + x;
            if (targetX < 0 || targetX >= image.width) continue;
            full[targetY * image.width + targetX] = cropped[y * bbox.width + x];
        }
    }
    return encodeBinaryMaskToRLE(full);
};

export const previewToCreateInput = ({
    preview,
    outputType,
    image
}: {
    preview: AnnotationPreview;
    outputType: OutputType;
    image: { width: number; height: number };
}): Omit<AnnotationCreateInput, 'annotation_label_id' | 'parent_sample_id'> => {
    const { x, y, width, height } = preview.bbox;
    if (outputType === 'box') {
        return { annotation_type: AnnotationType.OBJECT_DETECTION, x, y, width, height };
    }
    return {
        annotation_type: AnnotationType.SEGMENTATION_MASK,
        x,
        y,
        width,
        height,
        segmentation_mask: previewToFullImageRLE(preview, image)
    };
};

// The first non-blank candidate wins, e.g. the selected class before the predicted one.
export const resolveAnnotationClassName = (candidates: (string | null | undefined)[]): string =>
    candidates.map((candidate) => candidate?.trim()).find(Boolean) ?? 'object';

export const getAnnotationPreviewErrorMessage = (error: unknown): string => {
    if (error && typeof error === 'object') {
        const body = error as { error?: unknown; detail?: unknown };
        if (typeof body.error === 'string') return body.error;
        if (typeof body.detail === 'string') return body.detail;
    }
    if (error instanceof Error && error.message) return error.message;
    return 'Unknown error';
};
