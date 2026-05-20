import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { createImagesInfiniteOptions } from './createImagesInfiniteOptions';
import type { ImagesInfiniteParams } from './types';

export type { ImagesInfiniteParams } from './types';
export { buildRequestBody } from './buildRequestBody';

export const useImagesInfinite = (getParams: () => ImagesInfiniteParams) => {
    const samples = createInfiniteQuery(() => createImagesInfiniteOptions(getParams()));
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
