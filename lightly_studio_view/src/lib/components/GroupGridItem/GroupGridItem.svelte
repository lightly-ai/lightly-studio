<script lang="ts">
    import type { GroupView, ImageView, VideoView } from '$lib/api/lightly_studio_local/types.gen';
    import SampleImage from '../SampleImage/index.svelte';
    import VideoItem from '../VideoItem/VideoItem.svelte';

    let {
        sample,
        width,
        height,
        sample_count
    }: {
        sample: GroupView['group_preview'];
        width: number;
        height: number;
        sample_count: number;
    } = $props();
    const isVideo = (sample: GroupView['group_preview']): sample is VideoView => {
        return Boolean(sample && sample.type === 'video');
    };
    const isImage = (sample: GroupView['group_preview']): sample is ImageView => {
        return Boolean(sample && sample.type === 'image');
    };
</script>

<div class="relative h-full w-full" style="width: {width}px; height: {height}px">
    {#if isVideo(sample)}
        <VideoItem video={sample} size={width} showCaption={true} />
    {:else if isImage(sample)}
        <SampleImage {sample} {width} {height} />
    {/if}
    {#if sample_count > 1}
        <div
            class="absolute bottom-1 right-1 rounded-sm bg-black/60 px-1.5 py-0.5 text-xs font-bold text-white"
        >
            +{sample_count - 1}
        </div>
    {/if}
</div>
