<script lang="ts">
    import { AlertTriangle, Loader2 } from '@lucide/svelte';
    import { getMcapRecordingURLById } from '$lib/utils/getMcapRecordingURLById/getMcapRecordingURLById';
    import { ProviderError } from '../provider';
    import { probeFirstFrame, type ProbeResult, type ProbeTelemetry } from './providerProbe';

    /**
     * Temporary read-out of what the MCAP frame provider actually got (LIG-10661).
     *
     * The 3D scene lands in a later issue, so until then this reads one frame through the
     * real provider -- byte ranges, worker, decoder, cache -- and reports the recording's
     * channels, the frame's point counts, and every load/decode/cache timing. Each timing is
     * also logged to the console under `[mcap-provider]`. Delete this component once the
     * viewport renders frames.
     */
    interface Props {
        sampleId: string;
    }

    let { sampleId }: Props = $props();

    let phase = $state('idle');
    let result = $state<ProbeResult | undefined>(undefined);
    let failure = $state<string | undefined>(undefined);
    let failureDetail = $state<string | undefined>(undefined);
    let telemetry = $state<ProbeTelemetry[]>([]);

    const log = (message: string, detail?: unknown) =>
        console.info(`[mcap-provider] ${message}`, detail ?? '');

    $effect(() => {
        const recordingUrl = getMcapRecordingURLById(sampleId);
        let cancelled = false;
        // Kept outside the effect's reactive reads: reading `telemetry` back inside the
        // callback would make the effect depend on what it writes, and loop.
        const events: ProbeTelemetry[] = [];
        phase = 'starting';
        result = undefined;
        failure = undefined;
        failureDetail = undefined;
        telemetry = [];
        log('reading first frame', recordingUrl);

        void probeFirstFrame(sampleId, recordingUrl, {
            onPhase: (next) => {
                if (cancelled) return;
                phase = next;
                log(`phase: ${next}`);
            },
            onTelemetry: (event) => {
                if (cancelled) return;
                events.push(event);
                telemetry = events.slice(-8);
                log(`${event.operation}: ${event.durationMs.toFixed(1)} ms`, event);
            }
        })
            .then((probe) => {
                if (cancelled) return;
                result = probe;
                log('first frame decoded', probe);
            })
            .catch((error: unknown) => {
                if (cancelled) return;
                failure = error instanceof Error ? error.message : String(error);
                failureDetail = error instanceof ProviderError ? error.detail : undefined;
                log('failed', error);
            });

        return () => {
            cancelled = true;
        };
    });

    const megabytes = (bytes: string) => `${(Number(bytes) / 1024 ** 2).toFixed(1)} MB`;
</script>

<div
    class="pointer-events-auto absolute bottom-3 right-3 z-20 max-h-[calc(100%-1.5rem)] w-80 overflow-y-auto rounded-md border bg-background/95 p-3 text-xs shadow-lg"
    data-testid="workspace-provider-diagnostics"
>
    <div class="flex items-center gap-2 pb-2">
        {#if failure}
            <AlertTriangle class="size-4 text-destructive" aria-hidden="true" />
        {:else if !result}
            <Loader2 class="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
        {/if}
        <span class="font-medium">Frame provider</span>
        <span class="ml-auto font-mono text-muted-foreground">{phase}</span>
    </div>

    {#if failure}
        <p class="text-destructive" data-testid="provider-diagnostics-error">{failure}</p>
        {#if failureDetail}
            <p
                class="pt-1 font-mono text-muted-foreground"
                data-testid="provider-diagnostics-detail"
            >
                {failureDetail}
            </p>
        {/if}
    {:else if result}
        <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <dt class="text-muted-foreground">Recording</dt>
            <dd class="font-mono">{megabytes(result.sizeBytes)}</dd>
            <dt class="text-muted-foreground">Revision</dt>
            <dd class="truncate font-mono">{result.version}</dd>
            <dt class="text-muted-foreground">Frames listed</dt>
            <dd class="font-mono">
                {result.frameCount}{result.truncated ? '+' : ''}
            </dd>
            <dt class="text-muted-foreground">Points</dt>
            <dd class="font-mono">
                {result.pointCount.toLocaleString()} of {result.sourcePointCount.toLocaleString()}
            </dd>
            <dt class="text-muted-foreground">Log time</dt>
            <dd class="truncate font-mono">{result.logTimeNs}</dd>
        </dl>

        <p class="pt-2 text-muted-foreground">Channels</p>
        <ul class="pt-1">
            {#each result.topics as topic (topic.channelId)}
                <li class="flex gap-2 font-mono">
                    <span class={topic.supported ? '' : 'text-muted-foreground line-through'}>
                        {topic.topic}
                    </span>
                    <span class="ml-auto text-muted-foreground">{topic.messageCount ?? '?'}</span>
                </li>
            {/each}
        </ul>
    {/if}

    {#if telemetry.length > 0}
        <p class="pt-2 text-muted-foreground">Timings</p>
        <ul class="pt-1">
            {#each telemetry as event, index (index)}
                <li class="flex gap-2 font-mono">
                    <span>{event.operation}</span>
                    <span class="ml-auto text-muted-foreground">
                        {event.durationMs.toFixed(1)} ms
                        {#if event.bytesRead}· {(event.bytesRead / 1024).toFixed(0)} KB{/if}
                        {#if event.cacheHit}· hit{/if}
                    </span>
                </li>
            {/each}
        </ul>
    {/if}
</div>
