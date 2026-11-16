import { get2dEmbeddingsStatusOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export function useEmbeddingPlotStatus(getCollectionId: () => string) {
    return createQuery(() =>
        get2dEmbeddingsStatusOptions({ path: { collection_id: getCollectionId() } })
    );
}
