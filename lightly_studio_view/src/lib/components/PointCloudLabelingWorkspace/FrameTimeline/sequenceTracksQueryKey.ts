/**
 * A partial query key that matches the track coverage queries of one sequence, whatever frame
 * they were requested in. Use with `queryClient.invalidateQueries` after annotations are
 * created, deleted, relabeled, or attached to a track.
 */
export const getSequenceTracksSequenceQueryKey = ({
    datasetId,
    sequenceId
}: {
    datasetId: string;
    sequenceId: string;
}) => [{ _id: 'getSequenceTracks', path: { dataset_id: datasetId, sequence_id: sequenceId } }];
