<script lang="ts">
    import { PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import { goto } from '$app/navigation';
    import {
        getAllFrames,
        type FrameView,
        type SampleView,
        type VideoView
    } from '$lib/api/lightly_studio_local';
    import { page } from '$app/state';
    import { routeHelpers } from '$lib/routes';
    import { getGridFrameURL, getGridThumbnailRequestSize, getSimilarityColor } from '$lib/utils';
    import CanvasVideoPlayer from '../CanvasVideoPlayer/CanvasVideoPlayer.svelte';
    import VideoFrameAnnotationItem from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';

    let {
        video,
        size,
        showAnnotations = true,
        showCaption = false
    }: {
        video: VideoView;
        size: number;
        showAnnotations?: boolean;
        showCaption?: boolean;
    } = $props();

    let cursor = 0;
    let loading = false;
    let reachedEnd = false;
    const BATCH_SIZE = 50;
    let hoverTimer: ReturnType<typeof setTimeout> | null = null;
    const HOVER_DELAY = 200;
    let isHovering = $state(false);
    let showPreview = $state(false);
    let frames = $state<FrameView[]>(video.frame == null ? [] : [video.frame]);

    async function handleMouseEnter() {
        isHovering = true;
        hoverTimer = setTimeout(async () => {
            await loadFrames();

            if (!isHovering) {
                return;
            }

            showPreview = true;
        }, HOVER_DELAY);
    }

    function handleMouseLeave() {
        isHovering = false;
        if (hoverTimer) {
            clearTimeout(hoverTimer);
            hoverTimer = null;
        }
        showPreview = false;
    }

    const datasetId = $derived(page.params.dataset_id!);

    function handleOnDoubleClick() {
        const collectionId = (video.sample as SampleView).collection_id;

        if (datasetId && collectionId) {
            goto(
                routeHelpers.toVideosDetails({
                    datasetId,
                    collectionType: 'video',
                    collectionId,
                    sampleId: video.sample_id
                })
            );
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

        frames = Array.from(
            new Map([...frames, ...newFrames].map((frame) => [frame.sample_id, frame])).values()
        );
        cursor = res?.data?.nextCursor ?? cursor + BATCH_SIZE;

        loading = false;
    }
    const caption = $derived(
        showCaption && video.sample.captions?.length ? video.sample.captions[0] : null
    );
    const poster = $derived.by(() => {
        const frame = frames[0];
        if (!frame) {
            return null;
        }

        const requestedSize = getGridThumbnailRequestSize(
            size,
            globalThis.window?.devicePixelRatio || 1
        );

        return getGridFrameURL({
            sampleId: frame.sample_id,
            quality: 'high',
            renderedWidth: requestedSize,
            renderedHeight: requestedSize
        });
    });
</script>

<div
    class="video-frame-container relative overflow-hidden rounded-lg"
    ondblclick={handleOnDoubleClick}
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
    role="img"
    style={`width: var(${video.width}); height: var(${video.height});`}
>
    {#if showPreview && frames.length > 0}
        <CanvasVideoPlayer
            src={`${PUBLIC_VIDEOS_MEDIA_URL}/${video.sample_id}`}
            {frames}
            sampleWidth={video.width}
            sampleHeight={video.height}
            autoplay={true}
            muted={true}
            loop={true}
            lazyLoad={true}
            {showAnnotations}
            className="h-full w-full cursor-pointer rounded-lg shadow-md"
        />
    {:else if poster}
        <div class="relative h-full w-full overflow-hidden rounded-lg shadow-md">
            <img
                src={poster}
                alt={video.file_name}
                class="h-full w-full rounded-lg object-contain"
                draggable="false"
            />
            {#if showAnnotations && frames[0]}
                <!-- Scale SVG mask opacity (0.65) down to match CanvasVideoPlayer mask opacity (0.40) -->
                <div class="pointer-events-none absolute inset-0" style="opacity: {0.4 / 0.65}">
                    <VideoFrameAnnotationItem
                        width={size}
                        height={size}
                        sampleWidth={video.width}
                        sampleHeight={video.height}
                        sample={frames[0]}
                        showLabel={false}
                    />
                </div>
            {/if}
        </div>
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
