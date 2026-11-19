import type { LabelingModelsView } from '$lib/api/lightly_studio_local';

const POLL_INTERVAL_MS = 5_000;

// The server leaves out a model until its weights are loaded, so an empty list can change soon.
export const getLabelingModelsRefetchInterval = (
    models: LabelingModelsView | undefined
): number | false => (models && models.models.length > 0 ? false : POLL_INTERVAL_MS);
