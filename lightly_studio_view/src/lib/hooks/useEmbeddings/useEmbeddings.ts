import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    GetEmbeddings2dRequest,
    ImageFilter,
    VideoFilter
} from '$lib/api/lightly_studio_local/types.gen';

import { createQuery } from '@tanstack/svelte-query';

type EmbeddingsColorBy = GetEmbeddings2dRequest['color_by'];

export function useEmbeddings(
    collectionId: string,
    filters: ImageFilter | VideoFilter | null,
    colorBy: EmbeddingsColorBy = null
) {
    return createQuery(() =>
        get2dEmbeddingsOptions({
            path: { collection_id: collectionId },
            body: { filters: filters ?? {}, color_by: colorBy }
        })
    );
}
