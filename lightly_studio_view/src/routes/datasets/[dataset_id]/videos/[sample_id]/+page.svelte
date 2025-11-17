<script lang="ts">
    import { Card, CardContent, Segment } from '$lib/components';
    import { PUBLIC_VIDEOS_MEDIA_URL, PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { PageData } from './$types';
    import type { FrameView, VideoView } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components/ui';

    const { data }: { data: PageData } = $props();
    const { sample }: { sample: VideoView } = $derived(data);

    let videoEl: HTMLVideoElement | null = null;
    let currentFrame: FrameView | null = $state(onTimeUpdate());

    function onTimeUpdate(): FrameView | null {
        if (!sample.frames || sample.frames.length === 0 || !videoEl) return null;

        const currentTime = videoEl.currentTime;

        const pastFrames = sample.frames.filter((f) => f.frame_timestamp_s <= currentTime);

        const frame =
            pastFrames.length > 0
                ? pastFrames.reduce((prev, curr) =>
                      curr.frame_timestamp_s > prev.frame_timestamp_s ? curr : prev
                  )
                : sample.frames[0];

        currentFrame = frame;

        return frame;
    }
</script>

<div class="flex h-full w-full flex-row gap-4 overflow-hidden p-4">
    <Card className="flex flex-col w-[60vw]">
        <CardContent className="flex flex-col gap-4 overflow-hidden h-full">
            <video
                class="max-h-[100%] min-h-[100%] w-full rounded-lg object-contain shadow-md"
                src={`${PUBLIC_VIDEOS_MEDIA_URL}/${sample.sample_id}`}
                muted
                controls
                bind:this={videoEl}
                ontimeupdate={onTimeUpdate}
            ></video>
        </CardContent>
    </Card>

    <Card className="flex flex-col flex-1 overflow-hidden">
        <CardContent className="h-full overflow-y-auto">
            <Segment title="Sample details">
                <div class="text-diffuse-foreground min-w-full space-y-3">
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Width">Width:</span>
                        <span class="text-sm">{sample.width}px</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Height">Height:</span>
                        <span class="text-sm">{sample.height}px</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Duration">Duration:</span>
                        <span class="text-sm">{sample.duration_s.toFixed(2)} seconds</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="FPS">FPS:</span>
                        <span class="text-sm">{sample.fps.toFixed(2)}</span>
                    </div>
                </div>
            </Segment>
            <Segment title="Current Frame">
                {#if currentFrame}
                    <div class="text-diffuse-foreground space-y-2 text-sm">
                        <div class="flex items-center gap-2">
                            <span class="font-medium">Frame #:</span>
                            <span>{currentFrame.frame_number}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="font-medium">Timestamp:</span>
                            <span>{currentFrame.frame_timestamp_s.toFixed(3)} s</span>
                        </div>
                    </div>
                {/if}

                <Button variant="secondary" class="mt-4 w-full" href={'/'}>View frame</Button>
            </Segment>
        </CardContent>
    </Card>
</div>

<style>
    .no-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }
</style>
