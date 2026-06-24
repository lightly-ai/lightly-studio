import type { CreateEvaluationRunData } from '$lib/api/lightly_studio_local/types.gen';

type EvaluationRunRequest = CreateEvaluationRunData['body'];
export type EvaluationTaskType = EvaluationRunRequest['task_type'];

interface BuildEvaluationRunBodyParams {
    taskType: EvaluationTaskType;
    gtSource: string;
    predSource: string;
    collectionId: string;
    iouThreshold: number;
    classwise: boolean;
    /** Reference time for the auto-generated name. Defaults to now. */
    now?: Date;
}

const pad = (value: number): string => String(value).padStart(2, '0');

/**
 * Default run name using the browser's LOCAL time, e.g.
 * "object_detection 2026-06-24 10:15:33".
 *
 * Generated client-side (rather than letting the backend default to UTC) so the
 * timestamp in the name matches the localized `created_at` shown in the panel.
 */
export const defaultEvaluationRunName = (
    taskType: EvaluationTaskType,
    now: Date = new Date()
): string => {
    const stamp =
        `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ` +
        `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    return `${taskType} ${stamp}`;
};

/**
 * Build the request body for triggering an evaluation run.
 *
 * No filter is sent, so the run evaluates the full dataset. Object-detection
 * runs carry the IoU threshold and class-wise config; the other tasks have no
 * task-specific config. A local-time default name is included.
 */
export const buildEvaluationRunBody = (
    params: BuildEvaluationRunBodyParams
): EvaluationRunRequest => {
    const base = {
        gt_annotation_source: params.gtSource,
        pred_annotation_source: params.predSource,
        collection_id: params.collectionId,
        name: defaultEvaluationRunName(params.taskType, params.now)
    };
    if (params.taskType === 'object_detection') {
        return {
            ...base,
            task_type: 'object_detection',
            config: { iou_threshold: params.iouThreshold, classwise: params.classwise }
        };
    }
    return { ...base, task_type: params.taskType };
};

/** Whether the current selection can be submitted. */
export const canSubmitEvaluation = (params: {
    gtSource: string | undefined;
    predSource: string | undefined;
    isSubmitting: boolean;
}): boolean =>
    !!params.gtSource &&
    !!params.predSource &&
    params.gtSource !== params.predSource &&
    !params.isSubmitting;

/** Annotation type each evaluation task requires its sources to contain. */
const TASK_TO_ANNOTATION_TYPE: Record<EvaluationTaskType, string> = {
    object_detection: 'object_detection',
    classification: 'classification',
    semantic_segmentation: 'segmentation_mask'
};

/**
 * Whether an annotation source can be used for the given evaluation task.
 *
 * Mirrors the backend validator: every annotation in the source must be of the
 * task's expected type (and the source must contain at least one annotation).
 */
export const sourceMatchesTask = (
    annotationTypes: string[],
    taskType: EvaluationTaskType
): boolean => {
    const expected = TASK_TO_ANNOTATION_TYPE[taskType];
    return annotationTypes.length > 0 && annotationTypes.every((type) => type === expected);
};
