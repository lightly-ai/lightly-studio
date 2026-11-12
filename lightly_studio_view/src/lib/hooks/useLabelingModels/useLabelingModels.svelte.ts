import { createQuery } from '@tanstack/svelte-query';
import type { LabelingModelView } from '$lib/api/lightly_studio_local';
import { getLabelingModelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getLabelingModelsDisabledReason } from './getLabelingModelsDisabledReason';

interface UseLabelingModelsReturn {
    readonly models: LabelingModelView[];
    readonly disabledReason: string | null;
}

// Loads the labeling models that can run on the images of the collection.
export const useLabelingModels = (getCollectionId: () => string): UseLabelingModelsReturn => {
    const query = createQuery(() =>
        getLabelingModelsOptions({ query: { collection_id: getCollectionId() } })
    );
    const models = $derived(query.data?.models ?? []);
    const disabledReason = $derived(
        getLabelingModelsDisabledReason({ models: query.data, isError: query.isError })
    );

    return {
        get models() {
            return models;
        },
        get disabledReason() {
            return disabledReason;
        }
    };
};
