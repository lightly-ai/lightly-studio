import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { ImageFilter, VideoFilter } from '$lib/api/lightly_studio_local/types.gen';
import type { components } from '$lib/schema';

import { createQuery } from '@tanstack/svelte-query';

type MetadataFieldColorBy = components['schemas']['MetadataFieldColorBy'];

export function useEmbeddings(
    collectionId: string,
    filters: ImageFilter | VideoFilter | null,
    colorBy: MetadataFieldColorBy | null = null
) {
    return createQuery({
        ...get2dEmbeddingsOptions({
            path: { collection_id: collectionId },
            body: { filters: filters ?? {}, color_by: colorBy }
        })
    });
}
