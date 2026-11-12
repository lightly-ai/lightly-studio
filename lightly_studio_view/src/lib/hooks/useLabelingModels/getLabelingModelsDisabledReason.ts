import type { LabelingModelsView } from '$lib/api/lightly_studio_local';

interface GetLabelingModelsDisabledReasonParams {
    models: LabelingModelsView | undefined;
    isError: boolean;
}

// Returns why the label with model tool is disabled, or null if it is usable.
export const getLabelingModelsDisabledReason = ({
    models,
    isError
}: GetLabelingModelsDisabledReasonParams): string | null => {
    if (models) {
        if (models.models.length === 0) return 'No labeling model is registered.';
        return null;
    }
    if (isError) return 'Could not load the labeling models.';
    return 'Loading the labeling models…';
};
