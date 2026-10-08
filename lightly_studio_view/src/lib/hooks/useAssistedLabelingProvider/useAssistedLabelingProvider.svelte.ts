import { getAssistedLabelingProviderOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';
import { getAssistedLabelingTools } from './getAssistedLabelingTools';

export const useAssistedLabelingProvider = () => {
    const query = createQuery(() => getAssistedLabelingProviderOptions());
    const tools = $derived(
        getAssistedLabelingTools({ provider: query.data, isError: query.isError })
    );

    return {
        get tools() {
            return tools;
        }
    };
};
