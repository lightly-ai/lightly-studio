<script lang="ts">
    import type { FrameView, SampleView, VideoView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';
    import { goto } from '$app/navigation';
    import Video from '../Video/Video.svelte';

    let { video, size }: { video: VideoView; size: number } = $props();

    let videoEl: HTMLVideoElement | null = $state(null);

    function handleMouseEnter() {
        videoEl?.play();
    }

    function handleMouseLeave() {
        if (!videoEl) return;

        videoEl?.pause();
        videoEl.currentTime = 0;
    }

    function handleOnDoubleClick() {
        goto(
            routeHelpers.toVideosDetails((video.sample as SampleView).dataset_id, video.sample_id)
        );
    }

    let currentFrame: FrameView | null = $state(null);
</script>

<div
    class="video-frame-container relative overflow-hidden rounded-lg"
    ondblclick={handleOnDoubleClick}
    role="img"
    style={`width: var(${video.width}); height: var(${video.height});`}
>
    <Video
        bind:videoEl
        {video}
        update={(frame) => (currentFrame = frame)}
        muted={true}
        playsinline={true}
        preload="metadata"
        {handleMouseEnter}
        {handleMouseLeave}
        className="h-full w-full cursor-pointer rounded-lg shadow-md"
    />
    {#if currentFrame}
        <VideoFrameAnnotationItem
            width={size}
            height={size}
            sampleWidth={video.width}
            sampleHeight={video.height}
            sample={currentFrame}
        />
    {/if}
</div>

<style>
    .video-frame-container {
        cursor: pointer;
        background-color: black;

        width: 100%;
        height: 100%;
    }
</style>
