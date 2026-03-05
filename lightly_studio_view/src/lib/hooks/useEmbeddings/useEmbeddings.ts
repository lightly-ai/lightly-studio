import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { ImageFilter, VideoFilter } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery } from '@tanstack/svelte-query';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { derived } from 'svelte/store';

export function useEmbeddings(filters: StoreOrVal<ImageFilter | VideoFilter | null>) {
    const optionsStore = derived(toReadable(filters), (currentFilters) => ({
        ...get2dEmbeddingsOptions({
            body: { filters: currentFilters ?? {} }
        })
    }));
    return createQuery(optionsStore);
}
