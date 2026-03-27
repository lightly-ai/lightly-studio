import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { ImageFilter, VideoFilter } from '$lib/api/lightly_studio_local/types.gen';

import { createQuery } from '@tanstack/svelte-query';

export function useEmbeddings(collectionId: string, filters: ImageFilter | VideoFilter | null) {
    return createQuery({
        ...get2dEmbeddingsOptions({
            path: { collection_id: collectionId },
            body: { filters: filters ?? {} }
        })
    });
}
