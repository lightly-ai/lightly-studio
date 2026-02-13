<script lang="ts">
    import type { VideoFrameView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import Button from '../ui/button/button.svelte';

    const { frame, datasetId }: { frame: VideoFrameView; datasetId: string } = $props();
</script>

<Button
    variant="secondary"
    class="mt-4 w-full"
    data-testid="view-video-button"
    href={(() => {
        return routeHelpers.toVideosDetails(
            datasetId,
            'video',
            frame.video.sample.collection_id!,
            frame.video.sample_id,
            0,
            frame.frame_number
        );
    })()}
>
    View video
</Button>
