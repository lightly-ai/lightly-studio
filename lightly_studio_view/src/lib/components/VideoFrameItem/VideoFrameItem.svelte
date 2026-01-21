<script lang="ts">
    import { goto } from '$app/navigation';
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { SampleView, VideoFrameView } from '$lib/api/lightly_studio_local';
    import { routeHelpers } from '$lib/routes';
    import VideoFrameAnnotationItem from '../VideoFrameAnnotationItem/VideoFrameAnnotationItem.svelte';
    import { page } from '$app/state';

    let { videoFrame, index, size }: { videoFrame: VideoFrameView; index: number; size: number } =
        $props();

    const datasetId = $derived(page.params.dataset_id ?? page.data?.datasetId);
    const collectionType = $derived(page.params.collection_type ?? page.data?.collectionType);

    function handleOnDoubleClick() {
        if (datasetId && collectionType) {
            goto(
                routeHelpers.toFramesDetails(
                    datasetId,
                    collectionType,
                    (videoFrame.sample as SampleView).collection_id,
                    videoFrame.sample_id,
                    index
                )
            );
        }
    }
</script>

<div
    class="video-frame-container relative overflow-hidden rounded-lg"
    ondblclick={handleOnDoubleClick}
    role="img"
    style={`width: var(${videoFrame.video.width}); height: var(${videoFrame.video.height});`}
>
    <img
        src={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${videoFrame.sample_id}?compressed=true`}
        alt={`${videoFrame.sample_id}-${videoFrame.frame_number}`}
    />
    <VideoFrameAnnotationItem
        width={size}
        height={size}
        sampleWidth={videoFrame.video.width}
        sampleHeight={videoFrame.video.height}
        sample={videoFrame}
    />
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
