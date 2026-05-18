import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { createImagesInfiniteOptions } from './createImagesInfiniteOptions';
import type { ImagesInfiniteParams } from './types';

export type { ImagesInfiniteParams } from './types';
export { buildRequestBody } from './buildRequestBody';

export const useImagesInfinite = (params: ImagesInfiniteParams) => {
    const samplesOptions = createImagesInfiniteOptions(params);
    const samples = createInfiniteQuery(() => samplesOptions);
    const client = useQueryClient();

    const refresh = () => {
        client.invalidateQueries({ queryKey: samplesOptions.queryKey });
    };

    return {
        samples,
        refresh
    };
};
