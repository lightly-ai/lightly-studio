import { client } from '../dataset';

import { createQuery } from '@tanstack/svelte-query';

export const loadTagsCacheKey = (props: { dataset_id: string } | null) => {
    return ['/api/datasets/{dataset_id}/tags', props];
};

export const loadTagsCreateQuery = (props: { dataset_id: string } | null) => {
    const tags_createQuery = createQuery({
        enabled: props !== null,
        queryKey: loadTagsCacheKey(props),
        queryFn: () => {
            return client.GET('/api/datasets/{dataset_id}/tags', {
                params: {
                    path: {
                        dataset_id: props?.dataset_id || ''
                    }
                }
            });
        }
    });
    return tags_createQuery;
};
