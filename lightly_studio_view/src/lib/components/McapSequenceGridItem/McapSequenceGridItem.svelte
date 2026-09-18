<script lang="ts">
    import { BoxIcon } from '@lucide/svelte';
    import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
    import type { McapSequenceFrame } from '$lib/api/lightly_studio_local/types.gen';

    interface Props {
        sampleCount: number;
        width: number;
        height: number;
        sequenceFrame: McapSequenceFrame | null | undefined;
    }

    let { sampleCount, width, height, sequenceFrame }: Props = $props();

    const frameUrl = $derived(
        sequenceFrame
            ? `${PUBLIC_LIGHTLY_STUDIO_API_URL}datasets/${sequenceFrame.dataset_id}/recordings/${sequenceFrame.recording_id}/camera-frame` +
                  `?channel_id=${sequenceFrame.channel_id}` +
                  `&keyframe_timestamp_ns=${sequenceFrame.keyframe_log_time_ns}`
            : null
    );

    let imageError = $state(false);
</script>

<div
    data-testid="mcap-sequence-grid-item"
    class="relative h-full w-full"
    style="width: {width}px; height: {height}px"
>
    {#key frameUrl}
        {#if frameUrl !== null && !imageError}
            <img
                src={frameUrl}
                alt="MCAP sequence preview"
                class="h-full w-full object-cover"
                onerror={() => (imageError = true)}
            />
        {:else}
            <div
                class="flex h-full w-full flex-col items-center justify-center gap-2 bg-muted text-muted-foreground"
            >
                <BoxIcon class="size-10" />
                <span class="text-sm font-medium">MCAP sequence</span>
            </div>
        {/if}
    {/key}
    {#if sampleCount > 1}
        <div
            class="absolute bottom-1 right-1 rounded-sm bg-black/60 px-1.5 py-0.5 text-xs font-bold text-white"
            data-testid="mcap-sequence-frame-count"
        >
            +{sampleCount - 1}
        </div>
    {/if}
</div>
