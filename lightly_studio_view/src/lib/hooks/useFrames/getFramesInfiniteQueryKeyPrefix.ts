export const getFramesInfiniteQueryKeyPrefix = (collectionId: string) => [
    {
        _id: 'getAllFrames',
        _infinite: true,
        path: { video_frame_collection_id: collectionId }
    }
];
