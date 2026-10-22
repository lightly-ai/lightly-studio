import { createQuery } from '@tanstack/svelte-query';
import { getPluginCatalogOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

interface UsePluginCatalogParams {
    /** Fetch only when the catalog is visible, because the server fetches it from GitHub. */
    enabled: boolean;
}

/** Lists the plugins of the plugin catalog, and whether each one is installed. */
export const usePluginCatalog = (getParams: () => UsePluginCatalogParams) => {
    const query = createQuery(() => ({
        ...getPluginCatalogOptions(),
        enabled: getParams().enabled,
        // Without a network the catalog fails in the same way on each retry.
        retry: false,
        staleTime: 60_000
    }));
    return { query };
};
