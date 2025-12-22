import { embedTextOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createQuery } from '@tanstack/svelte-query';

type UseEmbedTextParams = {
    collectionId: string;
    queryText: string;
    embeddingModelId?: string | null;
};

export function useEmbedText({ collectionId, queryText, embeddingModelId }: UseEmbedTextParams) {
    const options = embedTextOptions({
        path: { collection_id: collectionId },
        query: {
            query_text: queryText,
            embedding_model_id: embeddingModelId
        }
    });
    return createQuery({
        ...options,
        enabled: Boolean(queryText)
    });
}
