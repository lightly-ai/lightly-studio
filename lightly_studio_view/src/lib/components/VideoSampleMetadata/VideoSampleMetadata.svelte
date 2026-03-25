<script lang="ts">
    import { type VideoView } from '$lib/api/lightly_studio_local';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import Typography from '$lib/components/Typography/Typography.svelte';

    const { video }: { video: VideoView } = $props();
</script>

<Segment title="Sample details">
    <dl class="grid grid-cols-[6rem_1fr] gap-y-3 text-diffuse-foreground">
        <Typography component="dt" variant="body2">File Name:</Typography>
        <Typography
            component="dd"
            variant="body2"
            className="break-all"
            props={{ 'data-testid': 'video-file-name' }}>{video.file_name}</Typography
        >
        <Typography component="dt" variant="body2">Width:</Typography>
        <Typography
            component="dd"
            variant="body2"
            className="break-all"
            props={{ 'data-testid': 'video-width' }}>{video.width}px</Typography
        >
        <Typography component="dt" variant="body2">Height:</Typography>
        <Typography
            component="dd"
            variant="body2"
            className="break-all"
            props={{ 'data-testid': 'video-height' }}>{video.height}px</Typography
        >
        {#if video.duration_s !== null && video.duration_s !== undefined}
            <Typography component="dt" variant="body2">Duration:</Typography>
            <Typography component="dd" variant="body2" className="break-all"
                >{video.duration_s.toFixed(2)} seconds</Typography
            >
        {/if}
        <Typography component="dt" variant="body2">FPS:</Typography>
        <Typography component="dd" variant="body2" className="break-all"
            >{video.fps.toFixed(2)}</Typography
        >
    </dl>
</Segment>
