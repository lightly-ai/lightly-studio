import type {
    ReadAnnotationsWithPayloadData,
    ReadAnnotationsWithPayloadRequest
} from '$lib/api/lightly_studio_local';

export type AnnotationsInfiniteParams = ReadAnnotationsWithPayloadData['path'] &
    Omit<ReadAnnotationsWithPayloadRequest, 'pagination'> & {
        /** False holds the request back, for example while a filter is still loading. */
        enabled?: boolean;
    };

export type AnnotationsInfiniteQueryKey = readonly [
    'readAnnotationsWithPayloadInfinite',
    string,
    Omit<AnnotationsInfiniteParams, 'collection_id'>
];
