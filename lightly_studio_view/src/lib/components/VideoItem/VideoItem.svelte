<script lang="ts">
    import { PUBLIC_VIDEOS_SAMPLES_URL } from "$env/static/public";
    import type { VideoView } from "$lib/api/lightly_studio_local";

    let { video }: { video: VideoView } = $props();
    
    let videoEl: HTMLVideoElement;

    function handleMouseEnter() {
        videoEl.play();
    }

    function handleMouseLeave() {
        videoEl.pause();
        videoEl.currentTime = 0;
    }
</script>
<video
    bind:this={videoEl}
    src={`${PUBLIC_VIDEOS_SAMPLES_URL}/${video.sample_id}`}
    muted
    playsinline
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
    class="h-full w-full cursor-pointer rounded-lg object-cover shadow-md"
></video>
