<script lang="ts">
    import { Card, CardContent, Segment } from '$lib/components';
    import { PUBLIC_VIDEOS_MEDIA_URL, PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { PageData } from './$types';
    import type { VideoView } from '$lib/api/lightly_studio_local';

    const { data }: { data: PageData } = $props();
    const { sample }: { sample: VideoView } = $derived(data);
</script>

<div class="flex h-full w-full flex-row gap-4 overflow-hidden p-4">
    <Card className="flex flex-col w-[60vw]">
        <CardContent className="flex flex-col gap-4 overflow-hidden h-full">
            <video
                class="max-h-[80%] min-h-[80%] w-full rounded-lg object-contain shadow-md"
                src={`${PUBLIC_VIDEOS_MEDIA_URL}/${sample.sample_id}`}
                muted
                controls
            ></video>

            <div class="no-scrollbar max-h-[20%] overflow-x-auto overflow-y-hidden">
                <div class="flex min-w-max gap-2 px-1 pb-2">
                    {#each sample.frames as frame}
                        <img
                            src={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${frame.sample_id}`}
                            alt="Frame"
                            class="h-20 w-28 shrink-0 cursor-pointer rounded-lg object-cover shadow-sm transition-transform duration-150 hover:scale-105"
                        />
                    {/each}
                </div>
            </div>
        </CardContent>
    </Card>

    <Card className="flex flex-col flex-1 overflow-hidden">
        <CardContent className="h-full overflow-y-auto">
            <Segment title="Sample details">
                <div class="min-w-full space-y-3 text-diffuse-foreground">
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
        </CardContent>
    </Card>
</div>

<style>
    .no-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }
</style>
