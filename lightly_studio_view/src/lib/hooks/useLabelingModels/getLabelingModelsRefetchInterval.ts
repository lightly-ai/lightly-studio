import type { LabelingModelsView } from '$lib/api/lightly_studio_local';

const POLL_INTERVAL_MS = 5_000;

// The server leaves out a model until its weights are loaded and reports that it is still loading.
export const getLabelingModelsRefetchInterval = (
    models: LabelingModelsView | undefined
): number | false => (models === undefined || models.has_loading_models ? POLL_INTERVAL_MS : false);
