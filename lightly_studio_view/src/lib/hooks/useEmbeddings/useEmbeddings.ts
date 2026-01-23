import { get2dEmbeddingsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { ImageFilter, VideoFilter } from '$lib/api/lightly_studio_local/types.gen';

import { createQuery } from '@tanstack/svelte-query';

type FilterWithType = ({ type: 'image' } & ImageFilter) | ({ type: 'video' } & VideoFilter);

export function useEmbeddings(filters?: ImageFilter | VideoFilter | null) {
    return createQuery({
        ...get2dEmbeddingsOptions(
            filters != null
                ? {
                      body: {
                          filters: filters as FilterWithType
                      }
                  }
                : {
                      body: {
                          filters: { type: 'image' } as FilterWithType
                      }
                  }
        ),
        enabled: filters != null
    });
}
