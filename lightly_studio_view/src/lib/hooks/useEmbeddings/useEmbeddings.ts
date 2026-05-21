import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type {
    GetEmbeddings2dRequest,
    ImageFilter,
    VideoFilter
} from '$lib/api/lightly_studio_local/types.gen';

import { createQuery } from '@tanstack/svelte-query';

type EmbeddingsColorBy = GetEmbeddings2dRequest['color_by'];
type EmbeddingsNlpAxes = GetEmbeddings2dRequest['nlp_axes'];
type EmbeddingsPcaAxes = GetEmbeddings2dRequest['pca_axes'];
type EmbeddingsReferenceLabelNames = GetEmbeddings2dRequest['reference_label_names'];

export function useEmbeddings(
    collectionId: string,
    filters: ImageFilter | VideoFilter | null,
    colorBy: EmbeddingsColorBy = null,
    nlpAxes: EmbeddingsNlpAxes = null,
    pcaAxes: EmbeddingsPcaAxes = null,
    referenceLabelNames: EmbeddingsReferenceLabelNames = null
) {
    return createQuery(() =>
        get2dEmbeddingsOptions({
            path: { collection_id: collectionId },
            body: {
                filters: filters ?? {},
                color_by: colorBy,
                nlp_axes: nlpAxes,
                pca_axes: pcaAxes,
                reference_label_names: referenceLabelNames
            }
        })
    );
}
