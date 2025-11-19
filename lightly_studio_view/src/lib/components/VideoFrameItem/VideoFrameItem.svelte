<script lang="ts">
    import { goto } from '$app/navigation';
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { SampleView, VideoFrameView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';

    let { videoFrame, index }: { videoFrame: VideoFrameView; index: number } = $props();

    function handleOnDoubleClick() {
        goto(
            routeHelpers.toFramesDetails(
                (videoFrame.sample as SampleView).dataset_id,
                videoFrame.sample_id,
                index
            )
        );
    }
</script>

<img
    ondblclick={handleOnDoubleClick}
    src={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${videoFrame.sample_id}`}
    alt={`${videoFrame.sample_id}-${videoFrame.frame_number}`}
/>

<style>
    img {
        object-fit: cover;
        background-color: black;

        width: 100%;
        height: 100%;
        object-fit: cover;

        cursor: pointer;
    }
</style>
