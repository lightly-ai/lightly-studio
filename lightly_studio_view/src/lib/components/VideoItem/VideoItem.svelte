<script lang="ts">
    import {
        getAllFrames,
        type FrameView,
        type SampleView,
        type VideoFrameView,
        type VideoView
    } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';
    import { goto } from '$app/navigation';
    import Video from '../Video/Video.svelte';

    let { video, size }: { video: VideoView; size: number } = $props();

    let videoEl: HTMLVideoElement | null = $state(null);

    let currentFrame: FrameView | null = $state(null);

    // Start it with the initial frame
    let frames = $state<FrameView[]>([]);

    async function handleMouseEnter() {
        frames = []
        await loadFrames(0);
        if (videoEl) {
            // Check if the video has enough data
            if (videoEl.readyState < 2) {
                // Wait the video loads enough
                await new Promise((res) =>
                    videoEl?.addEventListener('loadeddata', res, { once: true })
                );
            }
            videoEl.play();
        }
    }

    function handleMouseLeave() {
        if (!videoEl) return;

        videoEl?.pause();
        videoEl.currentTime = 0;
        frames = []
    }

    function handleOnDoubleClick() {
        goto(
            routeHelpers.toVideosDetails((video.sample as SampleView).dataset_id, video.sample_id)
        );
    }

    function onUpdate(frame: FrameView | VideoFrameView | null, index: number | null) {
        currentFrame = frame;
        if (index != null && index % 25 == 0 && index != 0) {
            loadFrames(index);
        }
    }

    async function loadFrames(cursor: number) {
        let framesWithAnnotations = await getAllFrames({
            path: {
                // Set the correct dataset
                video_frame_dataset_id: video.frames[0].sample.dataset_id,
            },
            query: {
                cursor,
                video_id: video.sample_id,
                limit: 25
            }
        });

        frames = [...frames, ...(framesWithAnnotations?.data?.data ?? [])];
    }
</script>

<div
    class="video-frame-container relative overflow-hidden rounded-lg"
    ondblclick={handleOnDoubleClick}
    role="img"
    style={`width: var(${video.width}); height: var(${video.height});`}
>
    <Video
        bind:videoEl
        video={{
            ...video,
            frames
        }}
        update={onUpdate}
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

    :global(.sample-annotation *) {
        pointer-events: none;
    }
</style>
