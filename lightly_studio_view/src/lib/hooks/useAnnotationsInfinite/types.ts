import type {
    ReadAnnotationsWithPayloadData,
    ReadAnnotationsWithPayloadRequest
} from '$lib/api/lightly_studio_local';

export type AnnotationsInfiniteParams = ReadAnnotationsWithPayloadData['path'] &
    Omit<ReadAnnotationsWithPayloadRequest, 'pagination'>;

export type AnnotationsInfiniteQueryKey = readonly [
    'readAnnotationsWithPayloadInfinite',
    string,
    Omit<AnnotationsInfiniteParams, 'collection_id'>
];
