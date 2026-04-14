<script lang="ts">
    import {
        getAllFrames,
        type FrameView,
        type SampleView,
        type VideoView
    } from '$lib/api/lightly_studio_local';
    import { page } from '$app/state';
    import { routeHelpers } from '$lib/routes';
    import {
        getGridFrameURL,
        getGridThumbnailRequestSize,
        getSimilarityColor,
        getVideoURLById
    } from '$lib/utils';
    import CanvasVideoPlayer from '$lib/components/CanvasVideoPlayer/CanvasVideoPlayer.svelte';
    import VideoFrameAnnotationItem from '$lib/components/VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';
    import { useSettings } from '$lib/hooks/useSettings';
    import { goto } from '$app/navigation';

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

    let loading = false;
    let hasLoadedAllFrames = false;
    let hoverTimer: ReturnType<typeof setTimeout> | null = null;
    const HOVER_DELAY = 200;
    let isHovering = false;
    let showPreview = $state(false);
    let frames = $state<FrameView[]>(video.frame == null ? [] : [video.frame]);
    const { gridViewSampleRenderingStore, gridViewThumbnailQualityStore } = useSettings();

    const datasetId = $derived(page.params.dataset_id!);
    const caption = $derived(
        showCaption && video.sample.captions?.length ? video.sample.captions[0] : null
    );
    const posterUrl = $derived.by(() => {
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
            quality: $gridViewThumbnailQualityStore,
            renderedWidth: requestedSize,
            renderedHeight: requestedSize
        });
    });

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
        showPreview = false;
        if (hoverTimer) {
            clearTimeout(hoverTimer);
            hoverTimer = null;
        }
    }

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
        if (loading || hasLoadedAllFrames) return;
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
            body: {
                filter: {
                    video_id: video.sample_id
                }
            }
        });

        const newFrames = res?.data?.data ?? [];
        frames = Array.from(new Map(newFrames.map((frame) => [frame.sample_id, frame])).values());
        hasLoadedAllFrames = true;
        loading = false;
    }
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
            src={getVideoURLById(video.sample_id)}
            {frames}
            sampleWidth={video.width}
            sampleHeight={video.height}
            initialFrameIndex={0}
            objectFit={$gridViewSampleRenderingStore}
            showControls={false}
            {showAnnotations}
            autoplay={true}
            loop={true}
            className="h-full w-full cursor-pointer rounded-lg shadow-md"
        />
    {:else if posterUrl}
        <div class="relative h-full w-full overflow-hidden rounded-lg shadow-md">
            <img
                src={posterUrl}
                alt={video.file_name}
                class={`h-full w-full rounded-lg ${
                    $gridViewSampleRenderingStore === 'cover' ? 'object-cover' : 'object-contain'
                }`}
                draggable="false"
            />
            {#if showAnnotations && frames[0]}
                <VideoFrameAnnotationItem
                    width={size}
                    height={size}
                    sampleWidth={video.width}
                    sampleHeight={video.height}
                    sample={frames[0]}
                    showLabel={false}
                    sampleImageObjectFit={$gridViewSampleRenderingStore}
                />
            {/if}
        </div>
    {:else}
        <div class="h-full w-full rounded-lg bg-black shadow-md"></div>
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
    img {
        user-select: none;
    }
</style>
