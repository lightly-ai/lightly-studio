<script lang="ts">
    import { Camera } from '@lucide/svelte';
    import * as Dialog from '$lib/components/ui/dialog';
    import { getCameraFrameUrl } from '../getCameraFrameUrl/getCameraFrameUrl';

    /**
     * A single camera tile in the projection strip. Renders the channel's frame
     * for the active tick, falling back to a placeholder camera icon when the
     * image fails to load. Clicking the frame enlarges it in a dialog over the
     * workspace; the enlarged frame follows the active tick.
     */
    interface Props {
        /** Dataset the recording belongs to. */
        datasetId: string;
        /** Recording that owns the frame. */
        recordingId?: string;
        /** MCAP channel to render. */
        channelId: number;
        /** Keyframe to decode from, in nanoseconds, as a string to preserve full precision. */
        keyframeTimestampNs?: string;
        /** Frame to show, in nanoseconds, as a string to preserve full precision. */
        logTimeNs?: string;
        /** Studio slot name shown as the caption, e.g. `front`. */
        label: string;
    }

    let { datasetId, recordingId, channelId, keyframeTimestampNs, logTimeNs, label }: Props =
        $props();

    const frameUrl = $derived(
        recordingId && keyframeTimestampNs && logTimeNs
            ? getCameraFrameUrl({
                  datasetId,
                  recordingId,
                  channelId,
                  keyframeTimestampNs,
                  logTimeNs
              })
            : null
    );

    let failedFrameUrl = $state<string | null>(null);
    let isEnlarged = $state(false);
</script>

<figure
    class="flex aspect-square h-full shrink-0 flex-col overflow-hidden rounded-md border bg-muted/30"
>
    {#if frameUrl && frameUrl !== failedFrameUrl}
        <button
            type="button"
            class="flex min-h-0 flex-1 cursor-zoom-in"
            aria-label={`Enlarge ${label}`}
            onclick={() => (isEnlarged = true)}
        >
            <img
                src={frameUrl}
                alt={label}
                class="min-h-0 flex-1 object-cover"
                onerror={() => (failedFrameUrl = frameUrl)}
            />
        </button>
        <Dialog.Root bind:open={isEnlarged}>
            <Dialog.Content class="max-w-[90vw] gap-2 p-3 sm:max-w-[90vw]">
                <Dialog.Title class="text-sm font-medium">{label}</Dialog.Title>
                <Dialog.Description class="sr-only">Enlarged camera frame</Dialog.Description>
                <img
                    src={frameUrl}
                    alt={`${label} enlarged`}
                    class="max-h-[80vh] w-full rounded-md object-contain"
                />
            </Dialog.Content>
        </Dialog.Root>
    {:else}
        <div class="flex min-h-0 flex-1 items-center justify-center text-muted-foreground">
            <Camera class="size-5" aria-hidden="true" />
        </div>
    {/if}
    <figcaption class="shrink-0 px-2 py-1 text-center text-xs text-muted-foreground">
        {label}
    </figcaption>
</figure>
