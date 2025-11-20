<script lang="ts">
    import { goto } from '$app/navigation';
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { SampleView, VideoFrameView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';

    let { videoFrame, index, size }: { videoFrame: VideoFrameView; index: number; size: number } =
        $props();

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

<div
    class="video-frame-container relative overflow-hidden rounded-lg"
    ondblclick={handleOnDoubleClick}
    role="img"
    style={`width: var(${videoFrame.video.width}); height: var(${videoFrame.video.height});`}
>
    <img
        src={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${videoFrame.sample_id}`}
        alt={`${videoFrame.sample_id}-${videoFrame.frame_number}`}
    />
    <VideoFrameAnnotationItem {size} sample={videoFrame} />
</div>

<style>
    img {
        width: 100%;
        height: 100%;
        object-fit: contain;
    }

    .video-frame-container {
        cursor: pointer;
        background-color: black;

        width: 100%;
        height: 100%;
    }
</style>
