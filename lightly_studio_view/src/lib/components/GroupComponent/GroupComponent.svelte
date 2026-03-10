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

<Badge variant="secondary" class="absolute m-2">{title}</Badge>
{#if type === 'image'}
    <Image className="w-60 h-60 object-contain" {src} />
{:else if type === 'video'}
    <VideoPreview className="w-60 h-60 object-contain" {src} />
{/if}
