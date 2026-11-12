import { createQuery } from '@tanstack/svelte-query';
import type { LabelingModelView } from '$lib/api/lightly_studio_local';
import { getLabelingModelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getLabelingModelsRefetchInterval } from './getLabelingModelsRefetchInterval';

interface UseLabelingModelsReturn {
    readonly models: LabelingModelView[];
    readonly isAvailable: boolean;
}

interface UseLabelingModelsParams {
    collectionId: string;
    enabled: boolean;
}

// Loads the labeling models that can run on the images of the collection. Each caller is a
// query observer that polls on its own, so each caller passes `enabled`.
export const useLabelingModels = (
    getParams: () => UseLabelingModelsParams
): UseLabelingModelsReturn => {
    const query = createQuery(() => {
        const { collectionId, enabled } = getParams();
        return {
            ...getLabelingModelsOptions({ query: { collection_id: collectionId } }),
            enabled,
            refetchInterval: ({ state }) => getLabelingModelsRefetchInterval(state.data)
        };
    });
    const models = $derived(query.data?.models ?? []);

    return {
        get models() {
            return models;
        },
        get isAvailable() {
            return models.length > 0;
        }
    };
};
