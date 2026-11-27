import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
import type { normalizedPointFromEvent } from '$lib/components/SampleDetails/useDragBox/useDragBox.helpers';

export type SmartSelectPoint = ReturnType<typeof normalizedPointFromEvent> & { positive: boolean };

// The provider rejects point prompts without a positive point.
export const canInferFromPoints = (points: SmartSelectPoint[]): boolean =>
    points.some((point) => point.positive);

// Uses the class of the most confident object detection under a positive click as a hint.
export const getClassNameAtPoint = (
    annotations: AnnotationView[],
    point: SmartSelectPoint,
    image: { width: number; height: number }
): string | null => {
    if (!point.positive) return null;
    const x = point.x * image.width;
    const y = point.y * image.height;
    const hits = annotations.filter((annotation) => {
        const box = annotation.object_detection_details;
        if (annotation.annotation_type !== AnnotationType.OBJECT_DETECTION || !box) return false;
        return x >= box.x && y >= box.y && x <= box.x + box.width && y <= box.y + box.height;
    });
    hits.sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0));
    return hits[0]?.annotation_label.annotation_label_name ?? null;
};
