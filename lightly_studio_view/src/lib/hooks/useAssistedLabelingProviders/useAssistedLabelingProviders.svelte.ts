import { createQuery } from '@tanstack/svelte-query';
import { listAssistedLabelingProvidersOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

export const useAssistedLabelingProviders = () => {
    const query = createQuery(() => listAssistedLabelingProvidersOptions());
    return { query };
};
