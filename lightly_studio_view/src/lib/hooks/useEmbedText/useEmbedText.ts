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
    const optionsStore = derived(toReadable(params), (currentParams) => {
        const options = embedTextOptions({
            path: { collection_id: currentParams.collectionId },
            query: {
                query_text: currentParams.queryText,
                embedding_model_id: currentParams.embeddingModelId
            }
        });
        return {
            ...options,
            enabled: Boolean(currentParams.queryText)
        };
    });
    return createQuery(optionsStore);
}
