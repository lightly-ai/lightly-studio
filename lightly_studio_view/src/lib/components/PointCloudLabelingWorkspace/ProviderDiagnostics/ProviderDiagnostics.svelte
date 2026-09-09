<script lang="ts">
    import { AlertTriangle, ChevronLeft, ChevronRight, Loader2 } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { useRecordingProbe } from './useRecordingProbe.svelte';

    /**
     * Temporary read-out of what the MCAP frame provider actually got (LIG-10661).
     *
     * The 3D scene lands in a later issue, so until then this reads frames through the real
     * session -- byte ranges, worker, decoder, query cache -- and reports the recording's
     * channels, each frame's point counts, and every open/list/decode timing. Stepping loads
     * one frame at a time, which is what the timeline will do; stepping back is a cache hit.
     * Timings are also logged under `[mcap-provider]`. Delete this component once the viewport
     * renders frames.
     */
    interface Props {
        sampleId: string;
    }

    let { sampleId }: Props = $props();

    const probe = useRecordingProbe(() => sampleId);

    const megabytes = (bytes: string) => `${(Number(bytes) / 1024 ** 2).toFixed(1)} MB`;
</script>

<div
    class="pointer-events-auto absolute bottom-3 right-3 z-20 max-h-[calc(100%-1.5rem)] w-80 overflow-y-auto rounded-md border bg-background/95 p-3 text-xs shadow-lg"
    data-testid="workspace-provider-diagnostics"
>
    <div class="flex items-center gap-2 pb-2">
        {#if probe.failure}
            <AlertTriangle class="size-4 text-destructive" aria-hidden="true" />
        {:else if probe.isLoading}
            <Loader2 class="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
        {/if}
        <span class="font-medium">Frame provider</span>
        <span class="ml-auto font-mono text-muted-foreground">{probe.phase}</span>
    </div>

    {#if probe.failure}
        <p class="text-destructive" data-testid="provider-diagnostics-error">{probe.failure}</p>
        {#if probe.failureDetail}
            <p
                class="pt-1 font-mono text-muted-foreground"
                data-testid="provider-diagnostics-detail"
            >
                {probe.failureDetail}
            </p>
        {/if}
    {:else if probe.recording}
        {@const recording = probe.recording}
        <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <dt class="text-muted-foreground">Recording</dt>
            <dd class="font-mono">{megabytes(recording.sizeBytes)}</dd>
            <dt class="text-muted-foreground">Channel</dt>
            <dd class="truncate font-mono">{recording.topic}</dd>
            <dt class="text-muted-foreground">Timeline</dt>
            <dd class="font-mono">
                {recording.durationSeconds.toFixed(1)} s
                {#if recording.frameRateHz}
                    · {recording.frameRateHz.toFixed(1)} Hz
                {/if}
            </dd>
            <dt class="text-muted-foreground">Revision</dt>
            <dd class="truncate font-mono">{recording.version}</dd>
            {#if probe.frame}
                {@const frame = probe.frame}
                <dt class="text-muted-foreground">Points</dt>
                <dd class="font-mono">
                    {(frame.positions.length / 3).toLocaleString()} of {frame.sourcePointCount.toLocaleString()}
                </dd>
                <dt class="text-muted-foreground">Log time</dt>
                <dd class="truncate font-mono">{frame.timestamp.nanoseconds}</dd>
            {/if}
        </dl>

        <div class="flex items-center gap-2 pt-2">
            <Button
                icon={ChevronLeft}
                variant="outline"
                ariaLabel="Previous frame"
                buttonProps={{
                    onclick: () => probe.step(probe.position - 1),
                    disabled: probe.position === 0
                }}
            />
            <span class="font-mono text-muted-foreground" data-testid="provider-frame-position">
                {probe.position + 1} / {probe.frameCount}{probe.atLimit ? '+' : ''}
            </span>
            <Button
                icon={ChevronRight}
                variant="outline"
                ariaLabel="Next frame"
                buttonProps={{
                    onclick: () => probe.step(probe.position + 1),
                    disabled: probe.position >= probe.frameCount - 1
                }}
            />
        </div>

        <p class="pt-2 text-muted-foreground">Channels</p>
        <ul class="pt-1">
            {#each recording.topics as topic (topic.channelId)}
                <li class="flex gap-2 font-mono">
                    <span class={topic.supported ? '' : 'text-muted-foreground line-through'}>
                        {topic.topic}
                    </span>
                    <span class="ml-auto text-muted-foreground">{topic.messageCount ?? '?'}</span>
                </li>
            {/each}
        </ul>
    {/if}

    {#if probe.telemetry.length > 0}
        <p class="pt-2 text-muted-foreground">Timings</p>
        <ul class="pt-1">
            {#each probe.telemetry as event, position (position)}
                <li class="flex gap-2 font-mono">
                    <span>{event.operation}</span>
                    <span class="ml-auto text-muted-foreground">
                        {event.durationMs.toFixed(1)} ms
                        {#if event.bytesRead}· {(event.bytesRead / 1024).toFixed(0)} KB{/if}
                    </span>
                </li>
            {/each}
        </ul>
    {/if}
</div>
