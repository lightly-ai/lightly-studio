import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';

import { createQuery } from '@tanstack/svelte-query';

type EmbeddingsColorBy = GetEmbeddings2dRequest['color_by'];
type EmbeddingsAxes = GetEmbeddings2dRequest['axes'];
type EmbeddingsMarkerEmbeddings = GetEmbeddings2dRequest['marker_embeddings'];

export function useEmbeddings(
    collectionId: string,
    filters: GetEmbeddings2dRequest['filters'] | null,
    colorBy: EmbeddingsColorBy = null,
    axes: EmbeddingsAxes = null,
    markerEmbeddings: EmbeddingsMarkerEmbeddings = null
) {
    return createQuery(() =>
        get2dEmbeddingsOptions({
            path: { collection_id: collectionId },
            body: {
                filters: filters ?? {},
                color_by: colorBy,
                axes,
                marker_embeddings: markerEmbeddings
            }
        })
    );
}
