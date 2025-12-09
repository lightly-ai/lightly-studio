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

    let { video, size, index }: { video: VideoView; size: number; index: number } = $props();

    let videoEl: HTMLVideoElement | null = $state(null);

    let currentFrame: FrameView | null = $state(null);

    let cursor = 0;
    let loading = false;
    let reachedEnd = false;
    const BATCH_SIZE = 25;
    let hoverTimer: ReturnType<typeof setTimeout> | null = null;
    const HOVER_DELAY = 200;
    let isHovering = false;
    // Start it with the initial frame
    let frames = $state<FrameView[]>(video.frame == null ? [] : [video.frame]);

    async function handleMouseEnter() {
        isHovering = true;
        hoverTimer = setTimeout(async () => {
            await loadFrames();

            if (videoEl) {
                if (videoEl.readyState < 2) {
                    await new Promise((res) =>
                        videoEl?.addEventListener('loadeddata', res, { once: true })
                    );
                }
                if (isHovering) videoEl.play();
            }
        }, HOVER_DELAY);
    }

    function handleMouseLeave() {
        isHovering = false;
        if (hoverTimer) {
            clearTimeout(hoverTimer);
            hoverTimer = null;
        }

        if (!videoEl) return;

        videoEl?.pause();
        videoEl.currentTime = 0;
    }

    function handleOnDoubleClick() {
        goto(
            routeHelpers.toVideosDetails(
                (video.sample as SampleView).dataset_id,
                video.sample_id,
                index
            )
        );
    }

    function onUpdate(frame: FrameView | VideoFrameView | null, index: number | null) {
        currentFrame = frame;
        if (index != null && index % BATCH_SIZE == 0 && index != 0) {
            loadFrames();
        }
    }

    async function loadFrames() {
        if (loading || reachedEnd) return;
        loading = true;

        const res = await getAllFrames({
            path: {
                video_frame_dataset_id: (video.frame?.sample as SampleView).dataset_id
            },
            query: {
                cursor,
                limit: BATCH_SIZE
            },
            body: {
                filter: {
                    video_id: video.sample_id
                }
            }
        });

        const newFrames = res?.data?.data ?? [];

        if (newFrames.length === 0) {
            reachedEnd = true;
            loading = false;
            return;
        }

        frames = [...frames, ...newFrames];

        cursor = res?.data?.nextCursor ?? cursor + BATCH_SIZE;

        loading = false;
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
        {video}
        {frames}
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
