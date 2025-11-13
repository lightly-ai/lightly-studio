import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { ImageFilter } from '$lib/api/lightly_studio_local/types.gen';

import { createQuery } from '@tanstack/svelte-query';

export function useEmbeddings(filters?: ImageFilter | null) {
    return createQuery(
        get2dEmbeddingsOptions(
            filters
                ? {
                      body: {
                          filters
                      }
                  }
                : undefined
        )
    );
}
