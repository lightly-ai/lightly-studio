import { client } from '../collection';

import { createQuery } from '@tanstack/svelte-query';

export const loadTagsCacheKey = (props: { collection_id: string } | null) => {
    return ['/api/collections/{collection_id}/tags', props];
};

export const loadTagsCreateQuery = (props: { collection_id: string } | null) => {
    const tags_createQuery = createQuery({
        enabled: props !== null,
        queryKey: loadTagsCacheKey(props),
        queryFn: () => {
            return client.GET('/api/collections/{collection_id}/tags', {
                params: {
                    path: {
                        collection_id: props?.collection_id || ''
                    }
                }
            });
        }
    });
    return tags_createQuery;
};
