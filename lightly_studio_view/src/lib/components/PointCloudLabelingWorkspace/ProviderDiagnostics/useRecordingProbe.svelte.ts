import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { getMcapRecordingURLById } from '$lib/utils/getMcapRecordingURLById/getMcapRecordingURLById';
import {
    createRecordingSession,
    ProviderError,
    resolveMcapSource,
    type FrameLocator,
    type RecordingSession,
    type TelemetryEvent
} from '../provider';

/**
 * Locators listed up front.
 *
 * Listing reads message indexes, so a window is cheap, but it is still a window: stepping
 * loads what it needs rather than paying for the whole timeline now.
 */
const FRAME_WINDOW = 5;
/**
 * Frames are about 100 KB each and the query cache evicts by age, not by bytes, so this is
 * what bounds how much of a scrubbed timeline stays resident.
 */
const FRAME_GC_TIME_MS = 60_000;
const TELEMETRY_LIMIT = 8;

export interface ProbeRecording {
    sizeBytes: string;
    version: string;
    topics: RecordingSession['metadata']['topics'];
    topic: string;
    durationSeconds: number;
    /** Average messages per second on the read channel, or null when it reports no count. */
    frameRateHz: number | null;
}

/**
 * Reads frames from one recording through the real session, for the diagnostics panel.
 *
 * The session is a resource, so this hook owns its lifetime; the frames are values, so the
 * query client owns their caching, deduplication and cancellation. Stepping back is a cache
 * hit, and the next frame is prefetched behind the visible one rather than pre-empting it.
 */
export function useRecordingProbe(sampleId: () => string) {
    const client = useQueryClient();

    let session = $state<RecordingSession | undefined>(undefined);
    let phase = $state('idle');
    let failure = $state<string | undefined>(undefined);
    let failureDetail = $state<string | undefined>(undefined);
    let telemetry = $state<TelemetryEvent[]>([]);
    let index = $state(0);

    const log = (message: string, detail?: unknown) =>
        console.info(`[mcap-provider] ${message}`, detail ?? '');

    function fail(error: unknown) {
        failure = error instanceof Error ? error.message : String(error);
        failureDetail = error instanceof ProviderError ? error.detail : undefined;
        log('failed', error);
    }

    $effect(() => {
        const id = sampleId();
        const url = getMcapRecordingURLById(id);
        let cancelled = false;
        // Outside the effect's reactive reads: reading `telemetry` back inside the callback
        // would make the effect depend on what it writes, and loop.
        const events: TelemetryEvent[] = [];
        let opened: RecordingSession | undefined;
        phase = 'starting';
        session = undefined;
        index = 0;
        failure = undefined;
        failureDetail = undefined;
        telemetry = [];
        log('opening recording', url);

        void open(id, url, {
            onPhase: (next) => {
                if (cancelled) return;
                phase = next;
                log(`phase: ${next}`);
            },
            onTelemetry: (event) => {
                if (cancelled) return;
                events.push(event);
                telemetry = events.slice(-TELEMETRY_LIMIT);
                log(`${event.operation}: ${event.durationMs.toFixed(1)} ms`, event);
            }
        })
            .then((created) => {
                opened = created;
                if (cancelled) return created.dispose();
                session = created;
                log('recording open', created.metadata);
            })
            .catch((error: unknown) => {
                if (!cancelled) fail(error);
            });

        return () => {
            cancelled = true;
            opened?.dispose();
        };
    });

    const framesQuery = createQuery(() => ({
        queryKey: ['mcap-frames', session?.source.recordingId, session?.source.version],
        queryFn: ({ signal }: { signal: AbortSignal }) => listWindow(session!, signal),
        enabled: session !== undefined,
        staleTime: Infinity
    }));

    const frames = $derived<readonly FrameLocator[]>(framesQuery.data ?? []);
    const locator = $derived(frames[index]);

    const frameQuery = createQuery(() => ({
        ...frameOptions(session, locator),
        enabled: session !== undefined && locator !== undefined
    }));

    // Warm the next frame once the visible one has arrived. Safe now: a queued read cannot
    // pre-empt a visible one, and abandoning one that has not started costs nothing.
    $effect(() => {
        const next = frames[index + 1];
        if (!session || !frameQuery.data || !next) return;
        void client.prefetchQuery(frameOptions(session, next));
    });

    function frameOptions(current: RecordingSession | undefined, at: FrameLocator | undefined) {
        return {
            queryKey: [
                'mcap-frame',
                current?.source.recordingId,
                current?.source.version,
                at?.channelId,
                at?.logTimeNs,
                at?.occurrence
            ],
            queryFn: ({ signal }: { signal: AbortSignal }) => current!.readFrame(at!, {}, signal),
            gcTime: FRAME_GC_TIME_MS,
            staleTime: Infinity
        };
    }

    return {
        get phase() {
            return phase;
        },
        get failure() {
            return failure ?? errorMessage(framesQuery.error ?? frameQuery.error);
        },
        get failureDetail() {
            return failureDetail ?? errorDetail(framesQuery.error ?? frameQuery.error);
        },
        get telemetry() {
            return telemetry;
        },
        get recording() {
            return session ? describeRecording(session) : undefined;
        },
        get frameCount() {
            return frames.length;
        },
        get atLimit() {
            return frames.length === FRAME_WINDOW;
        },
        get position() {
            return index;
        },
        get frame() {
            return frameQuery.data;
        },
        get isLoading() {
            return framesQuery.isPending || frameQuery.isFetching;
        },
        step(next: number) {
            if (next >= 0 && next < frames.length) index = next;
        }
    };
}

async function open(
    sampleId: string,
    url: string,
    callbacks: { onPhase: (phase: string) => void; onTelemetry: (event: TelemetryEvent) => void }
): Promise<RecordingSession> {
    const source = await resolveMcapSource({
        sampleId,
        url,
        // The probe assumes one frame for every recording. Confirming the real sensor
        // convention per recording is part of resolving a source properly.
        coordinateFrameId: 'lidar'
    });
    return createRecordingSession({
        source,
        onProgress: callbacks.onPhase,
        onTelemetry: callbacks.onTelemetry
    });
}

async function listWindow(
    session: RecordingSession,
    signal: AbortSignal
): Promise<readonly FrameLocator[]> {
    const channel = supportedChannel(session);
    return session.listFrames(
        {
            channelId: channel.channelId,
            startTimeNs: session.metadata.firstLogTimeNs!,
            endTimeNs: session.metadata.lastLogTimeNs!,
            limit: FRAME_WINDOW
        },
        signal
    );
}

export function supportedChannel(session: RecordingSession) {
    const channel = session.metadata.topics.find((topic) => topic.supported);
    if (!channel || !session.metadata.firstLogTimeNs || !session.metadata.lastLogTimeNs) {
        throw new ProviderError(
            'schema',
            'This recording has no ROS 2 CDR PointCloud2 channel to read.'
        );
    }
    return channel;
}

export function describeRecording(session: RecordingSession): ProbeRecording {
    const channel = session.metadata.topics.find((topic) => topic.supported);
    const first = session.metadata.firstLogTimeNs;
    const last = session.metadata.lastLogTimeNs;
    const seconds = first && last ? Number(BigInt(last) - BigInt(first)) / 1e9 : 0;
    const count = channel?.messageCount;
    return {
        sizeBytes: session.source.sizeBytes,
        version: session.source.version,
        topics: session.metadata.topics,
        topic: channel?.topic ?? '',
        durationSeconds: seconds,
        frameRateHz: count && seconds > 0 ? Number(count) / seconds : null
    };
}

function errorMessage(error: Error | null | undefined) {
    return error ? error.message : undefined;
}

function errorDetail(error: Error | null | undefined) {
    return error instanceof ProviderError ? error.detail : undefined;
}
