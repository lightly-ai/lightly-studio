import { embedTextOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { createQuery } from '@tanstack/svelte-query';
import { derived } from 'svelte/store';

type UseEmbedTextParams = {
    collectionId: string;
    queryText: string;
    embeddingModelId?: string | null;
};

export function useEmbedText(params: StoreOrVal<UseEmbedTextParams>) {
    const optionsStore = derived(toReadable(params), ($p) => {
        const options = embedTextOptions({
            path: { collection_id: $p.collectionId },
            query: {
                query_text: $p.queryText,
                embedding_model_id: $p.embeddingModelId
            }
        });
        return {
            ...options,
            enabled: Boolean($p.queryText)
        };
    });
    return createQuery(optionsStore);
}
