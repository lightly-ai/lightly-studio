<script lang="ts">
    import type { VideoFrameView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import { Button } from '$lib/components';

    const { frame, datasetId }: { frame: VideoFrameView; datasetId: string } = $props();
</script>

<Button
    variant="secondary"
    buttonProps={{
        class: 'mt-4 w-full',
        'data-testid': 'view-video-button',
        href: (() => {
            return routeHelpers.toVideosDetails({
                datasetId,
                collectionType: 'video',
                collectionId: frame.video.sample.collection_id!,
                sampleId: frame.video.sample_id,
                frameNumber: frame.frame_number
            });
        })()
    }}
>
    View video
</Button>
