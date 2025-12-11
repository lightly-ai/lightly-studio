import { embedTextOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createQuery } from '@tanstack/svelte-query';

type UseEmbedTextParams = {
    datasetId: string;
    queryText: string;
    embeddingModelId?: string | null;
};

export function useEmbedText({ datasetId, queryText, embeddingModelId }: UseEmbedTextParams) {
    const options = embedTextOptions({
        path: { dataset_id: datasetId },
        query: embeddingModelId
            ? {
                  query_text: queryText,
                  embedding_model_id: embeddingModelId
              }
            : {
                  query_text: queryText
              }
    });
    return createQuery({
        ...options,
        enabled: Boolean(queryText)
    });
}
