<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { SampleView, VideoFrameView } from '$lib/api/lightly_studio_local';

    let { videoFrame }: { videoFrame: VideoFrameView } = $props();
</script>

<a
    href={`/datasets/${(videoFrame.sample as SampleView).dataset_id}/frames/${videoFrame.sample_id}`}
>
    <img
        src={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${videoFrame.sample_id}`}
        alt={`${videoFrame.sample_id}-${videoFrame.frame_number}`}
    />
</a>

<style>
    img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
</style>
