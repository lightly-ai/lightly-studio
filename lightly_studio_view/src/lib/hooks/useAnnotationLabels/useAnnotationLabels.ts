import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useAnnotationLabels = ({ collectionId }: { collectionId: string }) =>
    createQuery(
        readAnnotationLabelsOptions({
            path: { collection_id: collectionId }
        })
    );
