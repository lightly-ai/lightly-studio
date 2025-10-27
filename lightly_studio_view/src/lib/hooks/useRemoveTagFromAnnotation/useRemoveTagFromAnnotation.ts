import { removeTagFromAnnotationMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { get } from 'svelte/store';

export const useRemoveTagFromAnnotation = () => {
    const mutation = createMutation(removeTagFromAnnotationMutation());

    mutation.subscribe(() => undefined);

    const removeTagFromAnnotation = (annotationId: string, tagId: string) =>
        new Promise<void>((resolve, reject) => {
            get(mutation).mutate(
                {
                    path: {
                        annotation_id: annotationId,
                        tag_id: tagId
                    }
                },
                {
                    onSuccess: () => resolve(),
                    onError: (error) => reject(error)
                }
            );
        });

    return {
        removeTagFromAnnotation
    };
};
