<script lang="ts">
    import { Camera } from '@lucide/svelte';
    import type { CreateQueryResult } from '@tanstack/svelte-query';
    import type {
        McapSequenceSummary,
        ChannelSummaryView
    } from '$lib/api/lightly_studio_local/types.gen';

    /**
     * Horizontal strip of camera images for the active point-cloud frame.
     * Tiles are derived from the sequence summary's camera_channels; each one
     * fetches its first keyframe directly via an <img> src URL.
     */
    interface Props {
        datasetId: string;
        summary?: CreateQueryResult<McapSequenceSummary, Error>;
    }

    let { datasetId, summary }: Props = $props();

    const BASE_URL = 'http://localhost:8001';

    function cameraFrameUrl(recordingId: string, channelId: number, timestampNs: number): string {
        const params = new URLSearchParams({
            channel_id: String(channelId),
            keyframe_timestamp_ns: String(timestampNs)
        });
        return `${BASE_URL}/datasets/${encodeURIComponent(datasetId)}/recordings/${encodeURIComponent(recordingId)}/camera-frame?${params}`;
    }

    const channels: ChannelSummaryView[] = $derived(summary?.data?.camera_channels ?? []);
    const recordingId: string = $derived(summary?.data?.recording_id ?? '');
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background"
    data-testid="workspace-projection-strip"
>
    <div class="flex shrink-0 items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground">
        <span class="font-medium text-foreground">Cameras &amp; projections</span>
        <span>· synchronized with the 3D selection</span>
    </div>
    <div class="flex min-h-0 flex-1 gap-2 overflow-x-auto px-3 pb-2">
        {#if channels.length > 0}
            {#each channels as channel (channel.channel_id)}
                <figure
                    class="flex h-full min-w-40 shrink-0 flex-col overflow-hidden rounded-md border bg-muted/30"
                >
                    {#if channel.first_keyframe_log_time_ns != null}
                        <img
                            src={cameraFrameUrl(
                                recordingId,
                                channel.channel_id,
                                channel.first_keyframe_log_time_ns
                            )}
                            alt={channel.group_component_name}
                            class="min-h-0 flex-1 object-cover"
                        />
                    {:else}
                        <div
                            class="flex min-h-0 flex-1 items-center justify-center text-muted-foreground"
                        >
                            <Camera class="size-5" aria-hidden="true" />
                        </div>
                    {/if}
                    <figcaption
                        class="shrink-0 px-2 py-1 text-center text-xs text-muted-foreground"
                    >
                        {channel.group_component_name}
                    </figcaption>
                </figure>
            {/each}
        {:else}
            {#each [0, 1, 2, 3] as i (i)}
                <figure
                    class="flex h-full min-w-40 shrink-0 flex-col items-center justify-center gap-1 rounded-md border bg-muted/30 text-muted-foreground"
                >
                    <Camera class="size-5" aria-hidden="true" />
                    <figcaption class="px-2 text-center text-xs">Camera</figcaption>
                </figure>
            {/each}
        {/if}
    </div>
</div>
