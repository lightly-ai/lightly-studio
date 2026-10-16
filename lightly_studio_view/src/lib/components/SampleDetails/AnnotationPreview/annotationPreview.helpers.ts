import {
    AnnotationType,
    type AnnotationCreateInput,
    type AnnotationPreview
} from '$lib/api/lightly_studio_local';

export type SaveAs = 'mask' | 'box';
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

export const previewToCreateInput = ({
    preview,
    saveAs
}: {
    preview: AnnotationPreview;
    saveAs: SaveAs;
}): Omit<AnnotationCreateInput, 'annotation_label_id' | 'parent_sample_id'> => {
    const { x, y, width, height } = preview.bbox;
    if (saveAs === 'box') {
        return { annotation_type: AnnotationType.OBJECT_DETECTION, x, y, width, height };
    }
    return {
        annotation_type: AnnotationType.SEGMENTATION_MASK,
        x,
        y,
        width,
        height,
        segmentation_mask: preview.segmentation_mask
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
        if (Array.isArray(body.detail)) {
            const msg = (body.detail[0] as { msg?: unknown } | undefined)?.msg;
            if (typeof msg === 'string') return msg;
        }
    }
    if (error instanceof Error && error.message) return error.message;
    return 'Unknown error';
};
