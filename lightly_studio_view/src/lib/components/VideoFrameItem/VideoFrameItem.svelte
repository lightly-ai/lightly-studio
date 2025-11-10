<script lang="ts">
    import { PUBLIC_SAMPLES_URL, PUBLIC_VIDEOS_FRAMES_URL } from "$env/static/public";
    import type { VideoFrameView } from "$lib/api/lightly_studio_local";

    let { videoFrame }: { videoFrame: VideoFrameView } = $props();
</script>

<img src={`${PUBLIC_VIDEOS_FRAMES_URL}/${videoFrame.sample_id}`} alt={`${videoFrame.sample_id}-${videoFrame.frame_number}`} />
{PUBLIC_SAMPLES_URL}
<style>
    img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
</style>