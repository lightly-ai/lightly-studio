<script lang="ts">
    import { Card, CardContent, Segment } from '$lib/components';
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { PageData } from '../[sampleId]/$types';
    import type { VideoFrameView } from '$lib/api/lightly_studio_local';

    const { data }: { data: PageData } = $props();
    const { sample }: { sample: VideoFrameView } = $derived(data);
</script>

<div class="flex h-full w-full flex-row gap-4 overflow-hidden p-4">
    <Card className="flex flex-col w-[60vw]">
        <CardContent className="flex flex-col gap-4 overflow-hidden h-full">
            <img
                alt="Video frame details"
                class="max-h-[100%] min-h-[100%] w-full rounded-lg object-contain shadow-md"
                src={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${sample.sample_id}`}
            />
        </CardContent>
    </Card>

    <Card className="flex flex-col flex-1 overflow-hidden">
        <CardContent className="h-full overflow-y-auto">
            <Segment title="Video frame details">
                <div class="min-w-full space-y-3 text-diffuse-foreground">
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Width">Number:</span>
                        <span class="text-sm">{sample.frame_number}</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title="Height">Timestamp:</span>
                        <span class="text-sm">{sample.frame_timestamp_s.toFixed(2)} seconds</span>
                    </div>
                </div>
            </Segment>
        </CardContent>
    </Card>
</div>
