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

<div class="relative flex h-60 w-60 items-start justify-start">
    {#if type === 'image'}
        <Image className="object-contain" {src} />
    {:else if type === 'video'}
        <VideoPreview className="object-contain" {src} />
    {/if}
    <Badge variant="secondary" class="badge absolute m-2">{title}</Badge>
</div>
