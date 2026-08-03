import { useQueryClient } from '@tanstack/svelte-query';
import { getAnnotationsInfiniteQueryKeyPrefix } from '$lib/hooks/useAnnotationsInfinite/createAnnotationsInfiniteOptions';
import { getFramesInfiniteQueryKeyPrefix } from '$lib/hooks/useFrames/getFramesInfiniteQueryKeyPrefix';
import { getImagesInfiniteQueryKeyPrefix } from '$lib/hooks/useImagesInfinite/createImagesInfiniteOptions';

interface UseInvalidateAnnotationGridQueriesParams {
    collectionId: string;
}

export const getAnnotationGridQueryKeyPrefixes = (collectionId: string) => [
    getImagesInfiniteQueryKeyPrefix(collectionId),
    getFramesInfiniteQueryKeyPrefix(collectionId),
    getAnnotationsInfiniteQueryKeyPrefix(collectionId)
];

export const useInvalidateAnnotationGridQueries = ({
    collectionId
}: UseInvalidateAnnotationGridQueriesParams) => {
    const client = useQueryClient();

    return () => {
        for (const queryKey of getAnnotationGridQueryKeyPrefixes(collectionId)) {
            client.invalidateQueries({ queryKey });
        }
    };
};
