/**
 * Manual API client for evaluation run endpoints.
 * Replace with auto-generated code after running `npm run generate-api-client`.
 */

export type EvaluationRunView = {
    id: string;
    name: string;
    task_type: string;
    gt_annotation_collection_id: string;
    pred_annotation_collection_id: string;
    gt_collection_name: string;
    pred_collection_name: string;
    config_json: Record<string, unknown>;
    created_at: string;
};

export type ConfusionMatrixCell = {
    gt_label_id: string | null;
    pred_label_id: string | null;
    count: number;
};

export type ConfusionMatrixLabelView = {
    label_id: string;
    label_name: string;
};

export type ConfusionMatrixResponse = {
    cells: ConfusionMatrixCell[];
    labels: ConfusionMatrixLabelView[];
};

async function apiFetch<T>(url: string): Promise<T> {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API ${url} failed: ${res.status}`);
    return res.json() as Promise<T>;
}

export const listEvaluationRuns = (datasetId: string): Promise<EvaluationRunView[]> =>
    apiFetch(`/api/datasets/${datasetId}/evaluation_runs`);

export const getEvaluationRun = (runId: string): Promise<EvaluationRunView> =>
    apiFetch(`/api/evaluation_runs/${runId}`);

export const getConfusionMatrix = (runId: string): Promise<ConfusionMatrixResponse> =>
    apiFetch(`/api/evaluation_runs/${runId}/confusion_matrix`);

export type OverlayAnnotationView = {
    annotation_id: string;
    annotation_type: string;
    confidence: number | null;
    annotation_label: { annotation_label_name: string };
    object_detection_details: { x: number; y: number; width: number; height: number } | null;
};

export const getAnnotationsByParentSample = (
    collectionId: string,
    parentSampleId: string
): Promise<OverlayAnnotationView[]> =>
    apiFetch(`/api/collections/${collectionId}/annotations/by_parent/${parentSampleId}`);
