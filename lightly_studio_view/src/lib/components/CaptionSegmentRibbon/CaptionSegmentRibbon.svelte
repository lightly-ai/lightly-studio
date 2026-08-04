<script lang="ts">
    import { getVideoURLById } from '$lib/utils';
    import { captureVideoFrames } from './captureVideoFrames';
    import {
        DEFAULT_SEGMENT_SAMPLE_COUNT,
        formatTimestampS,
        getUniformTimestamps
    } from './captionSegmentRibbon.helpers';

    interface Props {
        videoId: string;
        startTimeS: number;
        endTimeS: number;
        sampleCount?: number;
    }

    const {
        videoId,
        startTimeS,
        endTimeS,
        sampleCount = DEFAULT_SEGMENT_SAMPLE_COUNT
    }: Props = $props();

    const THUMBNAIL_WIDTH = 160;

    const timestamps = $derived(getUniformTimestamps({ startTimeS, endTimeS, sampleCount }));

    let thumbnails = $state<(string | null)[]>([]);
    let hasFailed = $state(false);

    $effect(() => {
        const controller = new AbortController();
        // Plain array: the effect must never read `thumbnails`, only assign to it.
        const captured: (string | null)[] = timestamps.map(() => null);

        thumbnails = captured.slice();
        hasFailed = false;

        captureVideoFrames({
            videoUrl: getVideoURLById(videoId),
            timestampsS: timestamps,
            thumbnailWidth: THUMBNAIL_WIDTH,
            signal: controller.signal,
            onFrame: (index, objectUrl) => {
                captured[index] = objectUrl;
                thumbnails = captured.slice();
            }
        }).catch((error: unknown) => {
            if (controller.signal.aborted) return;
            hasFailed = true;
            console.error('Error extracting caption segment thumbnails:', error);
        });

        return () => {
            controller.abort();
            captured.forEach((objectUrl) => objectUrl && URL.revokeObjectURL(objectUrl));
        };
    });
</script>

<div class="flex flex-col gap-1" data-testid="caption-segment-ribbon">
    <div class="flex items-center gap-2 text-xs text-muted-foreground">
        <span>{formatTimestampS(startTimeS)} – {formatTimestampS(endTimeS)}</span>
        {#if hasFailed}
            <span class="text-destructive">Preview unavailable</span>
        {/if}
    </div>
    <div class="flex gap-px overflow-hidden rounded-sm bg-black">
        {#each timestamps as timestampS, index (index)}
            <div class="relative h-16 min-w-0 flex-1">
                {#if thumbnails[index]}
                    <img
                        src={thumbnails[index]}
                        alt={`Frame at ${formatTimestampS(timestampS)}`}
                        class="h-full w-full object-cover"
                        data-testid="caption-segment-frame"
                    />
                {:else}
                    <div class="h-full w-full animate-pulse bg-muted"></div>
                {/if}
                <span
                    class="absolute bottom-0 right-0 bg-black/60 px-1 text-[10px] leading-4 text-white"
                >
                    {formatTimestampS(timestampS)}
                </span>
            </div>
        {/each}
    </div>
</div>
