<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { VideoFrameView } from '$lib/api/lightly_studio_local';

    let { videoFrame }: { videoFrame: VideoFrameView } = $props();
</script>

<img
    src={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${videoFrame.sample_id}`}
    alt={`${videoFrame.sample_id}-${videoFrame.frame_number}`}
/>

<style>
    img {
        object-fit: cover;
        background-color: black;

        width: 100%;
        height: 100%;
    }
</style>
