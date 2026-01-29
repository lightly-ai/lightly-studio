<script lang="ts">
    import {
        getAllFrames,
        type FrameView,
        type SampleView,
        type VideoFrameView,
        type VideoView
    } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import { getSimilarityColor } from '$lib/utils';
    import VideoFrameAnnotationItem from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';
    import { goto } from '$app/navigation';
    import Video from '../Video/Video.svelte';
    import { page } from '$app/state';

    let {
        video,
        size,
        index,
        showAnnotations = true,
        showCaption = false,
    }: {
        video: VideoView;
        size: number;
        index?: number | undefined;
        showAnnotations?: boolean;
        showCaption?: boolean;
    } = $props();

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
            if (showAnnotations) await loadFrames();

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

    const datasetId = $derived(page.params.dataset_id!);

    function handleOnDoubleClick() {
        const collectionId = (video.sample as SampleView).collection_id;

        if (datasetId && collectionId) {
            goto(
                routeHelpers.toVideosDetails(
                    datasetId,
                    'video',
                    collectionId,
                    video.sample_id,
                    index
                )
            );
        }
    }

    function onUpdate(frame: FrameView | VideoFrameView | null, index: number | null) {
        if (!showAnnotations) return;
        currentFrame = frame;
        if (index != null && index % BATCH_SIZE == 0 && index != 0) {
            loadFrames();
        }
    }

    async function loadFrames() {
        if (loading || reachedEnd) return;
        loading = true;
        const collectionId = (video.frame?.sample as SampleView).collection_id;
        if (!collectionId) {
            loading = false;
            return;
        }
        const res = await getAllFrames({
            path: {
                video_frame_collection_id: collectionId
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

    const caption = $derived(
        showCaption && video.sample.captions?.length ? video.sample.captions[0] : null
    );
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
    {#if video.similarity_score !== undefined && video.similarity_score !== null}
        <div
            class="absolute bottom-1 right-1 z-10 flex items-center rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white backdrop-blur-sm"
        >
            <span
                class="mr-1.5 block h-2 w-2 rounded-full"
                style="background-color: {getSimilarityColor(video.similarity_score)}"
            ></span>
            {video.similarity_score.toFixed(2)}
        </div>
    {/if}
    {#if caption}
        <div
            class="pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-b-lg bg-black/60 px-2 py-1 text-xs font-medium text-white"
        >
            <span class="block truncate" title={caption.text}>
                {caption.text}
            </span>
        </div>
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
