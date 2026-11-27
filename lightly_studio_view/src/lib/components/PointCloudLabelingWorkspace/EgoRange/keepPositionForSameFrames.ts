interface EgoFrames {
    referenceFrameId: string;
    egoFrameId: string;
}

interface PreviousQuery {
    queryKey: readonly { query?: { target_frame_id?: string; ego_frame_id?: string } }[];
}

/**
 * Keeps the position of the previous tick while the next one loads, but only in the same
 * frames. A position in another frame would measure the range from the wrong point.
 */
export function keepPositionForSameFrames<T>(
    previous: T | undefined,
    previousQuery: PreviousQuery | undefined,
    frames: EgoFrames
): T | undefined {
    const previousFrames = previousQuery?.queryKey[0]?.query;
    const isSameFrames =
        previousFrames?.target_frame_id === frames.referenceFrameId &&
        previousFrames?.ego_frame_id === frames.egoFrameId;
    return isSameFrames ? previous : undefined;
}
