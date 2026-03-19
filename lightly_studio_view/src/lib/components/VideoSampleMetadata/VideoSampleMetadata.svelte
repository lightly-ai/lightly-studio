<script lang="ts">
    import { type VideoView } from '$lib/api/lightly_studio_local';
    import Segment from '$lib/components/Segment/Segment.svelte';

    const { video }: { video: VideoView } = $props();
</script>

<Segment title="Sample details">
    <div class="min-w-full space-y-3 text-diffuse-foreground">
        <div class="flex items-start gap-3">
            <span class="truncate text-sm font-medium" title="File Name">File Name:</span>
            <span class="text-sm" data-testid="video-file-name">{video.file_name}</span>
        </div>
        <div class="flex items-start gap-3">
            <span class="truncate text-sm font-medium" title="Width">Width:</span>
            <span class="text-sm" data-testid="video-width">{video.width}px</span>
        </div>
        <div class="flex items-start gap-3">
            <span class="truncate text-sm font-medium" title="Height">Height:</span>
            <span class="text-sm" data-testid="video-height">{video.height}px</span>
        </div>
        {#if video.duration_s}
            <div class="flex items-start gap-3">
                <span class="truncate text-sm font-medium" title="Duration">Duration:</span>
                <span class="text-sm">{video.duration_s.toFixed(2)} seconds</span>
            </div>
        {/if}
        <div class="flex items-start gap-3">
            <span class="truncate text-sm font-medium" title="FPS">FPS:</span>
            <span class="text-sm">{video.fps.toFixed(2)}</span>
        </div>
    </div>
</Segment>
