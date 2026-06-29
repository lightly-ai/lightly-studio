export type AnnotationsInfiniteQuery = {
    annotation_label_ids?: string[];
    tag_ids?: string[];
    sample_ids?: string[];
    text_embedding?: number[];
    limit?: number;
};

export type AnnotationsInfiniteProps = {
    path: {
        collection_id: string;
    };
    query?: AnnotationsInfiniteQuery;
};

export type AnnotationsInfiniteParams = {
    collection_id: string;
} & AnnotationsInfiniteQuery;

export type AnnotationsInfiniteQueryKey = readonly [
    'readAnnotationsWithPayloadInfinite',
    string,
    Omit<AnnotationsInfiniteQuery, never>
];

export const toAnnotationsInfiniteParams = (
    props: AnnotationsInfiniteProps
): AnnotationsInfiniteParams => ({
    collection_id: props.path.collection_id,
    ...props.query
});
