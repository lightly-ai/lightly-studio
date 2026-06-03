<script lang="ts">
    import type { Snippet } from 'svelte';
    import { ImageSizeControl } from '$lib/components';

    interface GridHeaderProps {
        showImageSizeControl?: boolean;
        children?: Snippet;
        selectionControls?: Snippet;
        auxControls?: Snippet;
    }

    let {
        showImageSizeControl = true,
        children,
        selectionControls,
        auxControls
    }: GridHeaderProps = $props();
</script>

<div class="my-2 flex flex-wrap items-center gap-x-4 gap-y-2">
    {#if children}
        <div class="min-w-[12rem] flex-1">
            {@render children()}
        </div>
    {:else}
        <div class="flex-1"></div>
    {/if}

    {@render selectionControls?.()}
    {#if showImageSizeControl}
        <ImageSizeControl />
    {/if}
    {@render auxControls?.()}
</div>
