import { createQuery } from '@tanstack/svelte-query';
import { countVideoFrameAnnotationsByVideoCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { type VideoFilter } from '$lib/api/lightly_studio_local';

export const useVideoAnnotationCounts = ({
    collectionId,
    filter
}: {
    collectionId: string;
    filter: VideoFilter;
}) =>
    createQuery(
        countVideoFrameAnnotationsByVideoCollectionOptions({
            path: { collection_id: collectionId },
            body: {
                filter
            }
        })
    );
