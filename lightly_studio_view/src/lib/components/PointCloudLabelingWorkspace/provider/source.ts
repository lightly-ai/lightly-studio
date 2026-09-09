import type { CoordinateFrame } from '../domain';

/** Boundary supplied by the future sample-to-recording endpoint adapter. */
export interface McapSource {
    recordingId: string;
    /** Changes when the recording contents change; included in cache identity. */
    version: string;
    url: string;
    sizeBytes: string;
    etag?: string;
    /** Explicitly confirmed sensor coordinate convention; never inferred from schema name. */
    coordinateFrame: CoordinateFrame;
    logClockId: string;
    publishClockId: string;
}

export interface FrameLocator {
    channelId: number;
    logTimeNs: string;
    /** Zero-based message occurrence for this channel at this exact log time. */
    occurrence: number;
}

export function frameIdentity(source: McapSource, locator: FrameLocator): string {
    return JSON.stringify([
        source.recordingId,
        locator.channelId,
        locator.logTimeNs,
        locator.occurrence
    ]);
}
