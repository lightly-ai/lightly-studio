/** One encoded video message, as a CompressedVideo channel carries it. */
export interface VideoChunk {
    readonly logTimeNs: bigint;
    readonly data: Uint8Array;
}

const START_CODE_LENGTH = 4;

/**
 * Whether a chunk can be decoded without the ones before it.
 *
 * H.264 and H.265 say so in the NAL unit type, which is why the payload has to be scanned at
 * all: a decoder fed a delta frame first produces nothing, and there is no other signal in an
 * MCAP message saying where a group of pictures begins. VP9 and AV1 chunks are each
 * independently decodable, so every one of them is an entry point.
 */
export function isKeyframe(format: string, data: Uint8Array): boolean {
    if (format === 'h264') return hasNalUnit(data, (byte) => (byte & 0x1f) === 5);
    if (format === 'h265' || format === 'hevc') {
        // 16..21 are the IRAP types: a picture the stream can be joined at.
        return hasNalUnit(data, (byte) => {
            const nalType = (byte >> 1) & 0x3f;
            return nalType >= 16 && nalType <= 21;
        });
    }
    return true;
}

function hasNalUnit(data: Uint8Array, matches: (headerByte: number) => boolean): boolean {
    for (let at = 0; at + START_CODE_LENGTH < data.length; at++) {
        const isStartCode =
            data[at] === 0 && data[at + 1] === 0 && data[at + 2] === 0 && data[at + 3] === 1;
        if (isStartCode && matches(data[at + START_CODE_LENGTH])) return true;
    }
    return false;
}

/**
 * The chunks a decoder needs to produce the picture shown at `targetLogTimeNs`.
 *
 * That is the last keyframe at or before the target, through the last chunk at or before it:
 * everything in between is a delta frame the target depends on. Chunks after the target are
 * dropped, so the slice ends on the picture being asked for.
 *
 * @returns The slice, keyframe first. Empty when no keyframe precedes the target, which is
 * what a window that opened mid-group looks like; widening the window is the caller's call.
 */
export function chunksForTarget(
    chunks: readonly VideoChunk[],
    targetLogTimeNs: bigint,
    format: string
): readonly VideoChunk[] {
    let keyframeIndex = -1;
    let targetIndex = -1;
    for (const [index, chunk] of chunks.entries()) {
        if (chunk.logTimeNs > targetLogTimeNs) break;
        targetIndex = index;
        if (isKeyframe(format, chunk.data)) keyframeIndex = index;
    }
    if (keyframeIndex < 0 || targetIndex < keyframeIndex) return [];
    return chunks.slice(keyframeIndex, targetIndex + 1);
}
