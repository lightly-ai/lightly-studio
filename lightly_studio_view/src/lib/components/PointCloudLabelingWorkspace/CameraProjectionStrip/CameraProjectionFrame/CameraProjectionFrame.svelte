<script lang="ts">
    import { Camera } from '@lucide/svelte';
    import { getCameraFrameUrl } from '../getCameraFrameUrl/getCameraFrameUrl';

    /**
     * A single camera tile in the projection strip. Renders the channel's frame
     * for the active tick, falling back to a placeholder camera icon when the
     * image fails to load.
     */
    interface Props {
        /** Dataset the recording belongs to. */
        datasetId: string;
        /** Recording that owns the frame. */
        recordingId: string;
        /** MCAP channel to render. */
        channelId: number;
        /** Frame timestamp in nanoseconds. */
        timestampNs: number;
        /** Studio slot name shown as the caption, e.g. `front`. */
        label: string;
    }

    let { datasetId, recordingId, channelId, timestampNs, label }: Props = $props();

    const frameUrl = $derived(
        getCameraFrameUrl({ datasetId, recordingId, channelId, timestampNs })
    );

    let failedFrameUrl = $state<string | null>(null);
</script>

<figure
    class="flex h-full min-w-40 shrink-0 flex-col overflow-hidden rounded-md border bg-muted/30"
>
    {#if frameUrl !== failedFrameUrl}
        <img
            src={frameUrl}
            alt={label}
            class="min-h-0 flex-1 object-cover"
            onerror={() => (failedFrameUrl = frameUrl)}
        />
    {:else}
        <div class="flex min-h-0 flex-1 items-center justify-center text-muted-foreground">
            <Camera class="size-5" aria-hidden="true" />
        </div>
    {/if}
    <figcaption class="shrink-0 px-2 py-1 text-center text-xs text-muted-foreground">
        {label}
    </figcaption>
</figure>
