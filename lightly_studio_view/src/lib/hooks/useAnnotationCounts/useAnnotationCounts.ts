import { createQuery } from '@tanstack/svelte-query';
import { countAnnotationsByCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

export const useAnnotationCounts = ({
    collectionId,
    options
}: {
    collectionId: string;
    options?: {
        filtered_labels?: string[];
        dimensions?: {
            min_width?: number;
            max_width?: number;
            min_height?: number;
            max_height?: number;
        };
    };
}) =>
    createQuery(
        countAnnotationsByCollectionOptions({
            path: { collection_id: collectionId },
            query: {
                ...(options?.filtered_labels && { filtered_labels: options.filtered_labels }),
                ...(options?.dimensions?.min_width && { min_width: options.dimensions.min_width }),
                ...(options?.dimensions?.max_width && { max_width: options.dimensions.max_width }),
                ...(options?.dimensions?.min_height && {
                    min_height: options.dimensions.min_height
                }),
                ...(options?.dimensions?.max_height && {
                    max_height: options.dimensions.max_height
                })
            }
        })
    );
