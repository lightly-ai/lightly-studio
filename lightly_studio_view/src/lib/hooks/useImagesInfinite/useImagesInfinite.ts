import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { createImagesInfiniteOptions } from './createImagesInfiniteOptions';
import type { ImagesInfiniteParams } from './types';

export type { ImagesInfiniteParams } from './types';
export { buildRequestBody } from './buildRequestBody';

export const useImagesInfinite = (
    getParams: () => ImagesInfiniteParams,
    /** Holds the request back while it returns false. */
    getEnabled: () => boolean = () => true
) => {
    const samples = createInfiniteQuery(() => {
        const options = createImagesInfiniteOptions(getParams());
        return { ...options, enabled: options.enabled && getEnabled() };
    });
    const client = useQueryClient();

    const refresh = () => {
        const options = createImagesInfiniteOptions(getParams());
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    return {
        samples,
        refresh
    };
};
