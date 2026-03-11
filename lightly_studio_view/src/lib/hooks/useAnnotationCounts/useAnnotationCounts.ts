import { createQuery } from '@tanstack/svelte-query';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import { countAnnotationsByCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

export const useAnnotationCounts = ({
    collectionId,
    filter
}: {
    collectionId: string;
    filter?: ImageFilter;
}) =>
    createQuery(
        countAnnotationsByCollectionOptions({
            path: { collection_id: collectionId },
            body: {
                ...(filter && { filter })
            }
        })
    );
