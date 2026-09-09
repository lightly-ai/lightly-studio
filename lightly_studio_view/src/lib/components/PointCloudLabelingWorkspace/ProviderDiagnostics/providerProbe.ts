import { createMcapFrameProvider, ProviderError, resolveMcapSource } from '../provider';

export interface ProbeTelemetry {
    operation: string;
    durationMs: number;
    cacheBytes: number;
    bytesRead?: number;
    cacheHit?: boolean;
}

export interface ProbeTopic {
    channelId: number;
    topic: string;
    schema: string;
    supported: boolean;
    messageCount: string | null;
}

export interface ProbeResult {
    sizeBytes: string;
    version: string;
    topics: readonly ProbeTopic[];
    firstLogTimeNs: string | null;
    lastLogTimeNs: string | null;
    frameCount: number;
    truncated: boolean;
    pointCount: number;
    sourcePointCount: number;
    frameId: string;
    logTimeNs: string;
}

export interface ProbeCallbacks {
    onPhase: (phase: string) => void;
    onTelemetry: (event: ProbeTelemetry) => void;
}

/**
 * Reads one point-cloud frame end to end so the workspace can show what the provider got.
 *
 * A temporary diagnostic: it exercises the same calls the renderer will make -- open,
 * listFrames, loadFrame -- and reports what came back instead of drawing it.
 *
 * @param sampleId - The MCAP sample whose recording to read.
 * @param recordingUrl - URL serving that recording as byte ranges.
 * @param callbacks - Progress and timing sinks.
 * @returns What the provider reported about the recording and its first frame.
 * @throws ProviderError - The recording has no supported channel, or reading it failed.
 */
export async function probeFirstFrame(
    sampleId: string,
    recordingUrl: string,
    callbacks: ProbeCallbacks
): Promise<ProbeResult> {
    const source = await resolveMcapSource({
        sampleId,
        url: recordingUrl,
        // The probe states one frame for every recording. Confirming the real sensor
        // convention per recording is part of resolving a source properly.
        coordinateFrameId: 'lidar'
    });
    const provider = createMcapFrameProvider({
        source,
        onProgress: callbacks.onPhase,
        onTelemetry: callbacks.onTelemetry
    });

    try {
        const metadata = await provider.open();
        const topics = metadata?.topics ?? [];
        const channel = topics.find((topic) => topic.supported);
        if (!channel || !metadata?.firstLogTimeNs || !metadata.lastLogTimeNs) {
            throw new ProviderError(
                'schema',
                'This recording has no ROS 2 CDR PointCloud2 channel to read.'
            );
        }

        const range = await provider.listFrames({
            channelId: channel.channelId,
            startTimeNs: metadata.firstLogTimeNs,
            endTimeNs: metadata.lastLogTimeNs
        });
        const first = range?.frames[0];
        if (!first) {
            throw new ProviderError('source', 'The recording has no frames in its time range.');
        }

        const frame = await provider.loadFrame(first);
        return {
            sizeBytes: source.sizeBytes,
            version: source.version,
            topics,
            firstLogTimeNs: metadata.firstLogTimeNs,
            lastLogTimeNs: metadata.lastLogTimeNs,
            frameCount: range.frames.length,
            truncated: range.truncated,
            pointCount: frame.positions.length / 3,
            sourcePointCount: frame.sourcePointCount,
            frameId: frame.id,
            logTimeNs: frame.timestamp.nanoseconds
        };
    } finally {
        provider.dispose();
    }
}
