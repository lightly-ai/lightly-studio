<script lang="ts">
    import { Image, VideoPreview } from '$lib/components';
    import { Badge } from '$lib/components/ui/badge/index.js';

    const {
        src,
        type,
        title
    }: {
        src: string;
        title: string;
        type: 'image' | 'video';
    } = $props();
</script>

<div class="relative flex h-40 w-40 items-start justify-start">
    {#if type === 'image'}
        <Image className="pointer-events-none object-contain" {src} />
    {:else if type === 'video'}
        <VideoPreview className="pointer-events-none object-contain" {src} />
    {/if}
    <Badge variant="secondary" class="badge absolute m-2">{title}</Badge>
</div>
