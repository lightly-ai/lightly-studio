<script lang="ts">
    import type { Snippet } from 'svelte';
    import { ImageSizeControl } from '$lib/components';

    let {
        showImageSizeControl = true,
        children,
        auxControls
    }: {
        showImageSizeControl?: boolean;
        children?: Snippet;
        auxControls?: Snippet;
    } = $props();
</script>

<div class="my-2 flex items-center space-x-4">
    <div class="flex-1">
        {@render children?.()}
    </div>

    {#if showImageSizeControl}
        <ImageSizeControl />
    {/if}
    {@render auxControls?.()}
</div>
