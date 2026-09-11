import { untrack } from 'svelte';
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
 * Locators listed before the first frame is shown.
 *
 * One, so opening a recording costs the summary index, a single message-index read and one
 * decode. Later frames are discovered as navigation reaches them, and the one after the
 * visible frame is listed and warmed in the background.
 */
const INITIAL_FRAMES = 1;
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

export type RecordingProbe = ReturnType<typeof useRecordingProbe>;

/**
 * Reads frames from one recording through the real session, for the scene and the panel.
 *
 * The session is a resource, so this hook owns its lifetime; the frames are values, so the
 * query client owns their caching, deduplication and cancellation. Stepping back is a cache
 * hit, and the next frame is prefetched behind the visible one rather than pre-empting it.
 *
 * @param sampleId - The MCAP sample to read. An empty id opens nothing, which is how a
 * caller waits for a feature flag or a route parameter.
 */
export function useRecordingProbe(sampleId: () => string) {
    const client = useQueryClient();

    let session = $state<RecordingSession | undefined>(undefined);
    let phase = $state('idle');
    let failure = $state<string | undefined>(undefined);
    let failureDetail = $state<string | undefined>(undefined);
    let telemetry = $state<TelemetryEvent[]>([]);
    let index = $state(0);
    /**
     * Locators found after the first, as navigation reached them.
     *
     * Raw, not deeply reactive: these are posted to a worker, and a deep state proxy cannot
     * be structured-cloned. The array is replaced rather than mutated, so assignment is all
     * the reactivity it needs.
     */
    let discovered = $state.raw<FrameLocator[]>([]);
    /** Set once a listing past the last known frame comes back empty. */
    let exhausted = $state(false);

    const log = (message: string, detail?: unknown) =>
        console.info(`[mcap-provider] ${message}`, detail ?? '');

    function fail(error: unknown) {
        failure = error instanceof Error ? error.message : String(error);
        failureDetail = error instanceof ProviderError ? error.detail : undefined;
        log('failed', error);
    }

    $effect(() => {
        const id = sampleId();
        if (!id) return;
        const url = getMcapRecordingURLById(id);
        let cancelled = false;
        // Outside the effect's reactive reads: reading `telemetry` back inside the callback
        // would make the effect depend on what it writes, and loop.
        const events: TelemetryEvent[] = [];
        let opened: RecordingSession | undefined;
        phase = 'starting';
        session = undefined;
        index = 0;
        discovered = [];
        exhausted = false;
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

    const firstQuery = createQuery(() => ({
        queryKey: ['mcap-frames', session?.source.recordingId, session?.source.version],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
            listFrom(session!, session!.metadata.firstLogTimeNs!, INITIAL_FRAMES, signal),
        enabled: session !== undefined,
        staleTime: Infinity
    }));

    const frames = $derived<readonly FrameLocator[]>([...(firstQuery.data ?? []), ...discovered]);
    const locator = $derived(frames[index]);

    const frameQuery = createQuery(() => ({
        ...frameOptions(session, locator),
        enabled: session !== undefined && locator !== undefined
    }));

    /**
     * Makes sure a frame after the current one is known, listing one more if not.
     *
     * @returns Whether there is a frame to move to.
     */
    async function ensureNext(): Promise<boolean> {
        const known = frames;
        const current = index;
        if (!session || known.length === 0) return false;
        if (known.length > current + 1) return true;
        if (exhausted) return false;

        const last = known[known.length - 1];
        // Start at the last known time rather than after it: a channel can carry several
        // messages at one log time, and those are separate frames.
        const found = await listFrom(session, last.logTimeNs, last.occurrence + 2);
        const ahead = found.filter((candidate) => isAfter(candidate, last));
        if (ahead.length === 0) {
            exhausted = true;
            return false;
        }
        discovered = [...discovered, ...ahead];
        return true;
    }

    // Warm the frame after the visible one, listing it first if it is not known yet. Safe
    // now: a queued read cannot pre-empt a visible one, and abandoning one that has not
    // started costs nothing. Untracked because it writes what it reads.
    $effect(() => {
        const current = session;
        if (!current || !frameQuery.data) return;
        untrack(() => {
            void ensureNext().then(() => {
                const next = frames[index + 1];
                if (next) void client.prefetchQuery(frameOptions(current, next));
            });
        });
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
            return failure ?? errorMessage(firstQuery.error ?? frameQuery.error);
        },
        get failureDetail() {
            return failureDetail ?? errorDetail(firstQuery.error ?? frameQuery.error);
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
        get hasMore() {
            return !exhausted;
        },
        get position() {
            return index;
        },
        get frame() {
            return frameQuery.data;
        },
        get isLoading() {
            return firstQuery.isPending || frameQuery.isFetching;
        },
        previous() {
            if (index > 0) index -= 1;
        },
        next() {
            void ensureNext().then((moved) => {
                if (moved) index += 1;
            });
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
        // The frame every sensor is aligned into, not the frame of any one of them: these
        // recordings publish their lidars relative to the vehicle cabin. The reader falls
        // back to the read channel's own frame when a recording names its vehicle frame
        // differently, so this stays a default rather than a requirement. Confirming it
        // per recording is part of resolving a source properly.
        coordinateFrameId: 'CABIN'
    });
    return createRecordingSession({
        source,
        onProgress: callbacks.onPhase,
        onTelemetry: callbacks.onTelemetry
    });
}

async function listFrom(
    session: RecordingSession,
    startTimeNs: string,
    limit: number,
    signal?: AbortSignal
): Promise<readonly FrameLocator[]> {
    const channel = supportedChannel(session);
    return session.listFrames(
        {
            channelId: channel.channelId,
            startTimeNs,
            endTimeNs: session.metadata.lastLogTimeNs!,
            limit
        },
        signal
    );
}

/** Log time order, with the occurrence breaking ties between messages sharing a time. */
function isAfter(candidate: FrameLocator, last: FrameLocator): boolean {
    const time = BigInt(candidate.logTimeNs);
    const lastTime = BigInt(last.logTimeNs);
    if (time !== lastTime) return time > lastTime;
    return candidate.occurrence > last.occurrence;
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
