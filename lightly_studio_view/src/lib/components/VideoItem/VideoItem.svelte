<script lang="ts">
    import { PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import type { FrameView, SampleView, VideoView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';
    import { goto } from '$app/navigation';

    let { video, size }: { video: VideoView; size: number } = $props();

    let videoEl: HTMLVideoElement;

    function handleMouseEnter() {
        videoEl.play();
    }

    function handleMouseLeave() {
        videoEl.pause();
        videoEl.currentTime = 0;
    }

    function handleOnDoubleClick() {
        goto(
            routeHelpers.toVideosDetails((video.sample as SampleView).dataset_id, video.sample_id)
        );
    }

    let currentFrame: FrameView | null = $state(onTimeUpdate());

    function onTimeUpdate(): FrameView | null {
        if (!video.frames || video.frames.length === 0 || !videoEl) return null;

        const currentTime = videoEl.currentTime;
        const pastFrames = video.frames.filter((f) => f.frame_timestamp_s <= currentTime);

        const frame =
            pastFrames.length > 0
                ? pastFrames.reduce((prev, curr) =>
                      curr.frame_timestamp_s > prev.frame_timestamp_s ? curr : prev
                  )
                : video.frames[0];

        currentFrame = frame;
        return frame;
    }
</script>

<div
    class="video-frame-container relative overflow-hidden rounded-lg"
    ondblclick={handleOnDoubleClick}
    role="img"
    style={`width: var(${video.width}); height: var(${video.height});`}
>
    <video
        bind:this={videoEl}
        src={`${PUBLIC_VIDEOS_MEDIA_URL}/${video.sample_id}#t=0.001`}
        muted
        playsinline
        preload="metadata"
        onmouseenter={handleMouseEnter}
        onmouseleave={handleMouseLeave}
        ontimeupdate={onTimeUpdate}
        class="h-full w-full cursor-pointer rounded-lg object-cover shadow-md"
    ></video>
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
    video {
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
