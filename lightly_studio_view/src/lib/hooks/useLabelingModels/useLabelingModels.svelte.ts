import { createQuery } from '@tanstack/svelte-query';
import type { LabelingModelView } from '$lib/api/lightly_studio_local';
import { getLabelingModelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getLabelingModelsRefetchInterval } from './getLabelingModelsRefetchInterval';

interface UseLabelingModelsReturn {
    readonly models: LabelingModelView[];
    readonly isAvailable: boolean;
}

// Each caller is a query observer that polls on its own, so each caller passes getEnabled.
export const useLabelingModels = (getEnabled: () => boolean): UseLabelingModelsReturn => {
    const query = createQuery(() => ({
        ...getLabelingModelsOptions(),
        enabled: getEnabled(),
        refetchInterval: ({ state }) => getLabelingModelsRefetchInterval(state.data)
    }));
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
