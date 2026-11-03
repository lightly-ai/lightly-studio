<script lang="ts">
    import { MousePointerClick, X } from '@lucide/svelte';
    import type { GridType } from '$lib/types';

    interface Props {
        gridType: GridType;
        tagKey: string;
        /** Omitted on grids without an Annotate menu. */
        annotateKey?: string;
        onDismiss: () => void;
    }

    let { gridType, tagKey, annotateKey, onDismiss }: Props = $props();

    const NOUNS: Record<GridType, string> = {
        images: 'images',
        annotations: 'annotations',
        captions: 'captions',
        video_frames: 'frames',
        videos: 'videos',
        groups: 'groups'
    };
</script>

{#snippet kbd(key: string)}
    <kbd class="rounded border border-border bg-muted px-1 font-mono text-xs uppercase">{key}</kbd>
{/snippet}

<div
    class="pointer-events-auto flex items-center gap-2 whitespace-nowrap rounded-xl border border-dashed border-muted-foreground/40 bg-background/80 px-3 py-1.5 text-xs text-muted-foreground backdrop-blur-sm"
    data-testid="selection-hint"
>
    <MousePointerClick class="h-3.5 w-3.5" />
    <span>
        Select {NOUNS[gridType]} to tag {@render kbd(tagKey)}
        {#if annotateKey}
            or annotate {@render kbd(annotateKey)}
        {/if}
    </span>
    <button
        class="flex h-5 w-5 items-center justify-center rounded-full hover:bg-muted hover:text-foreground"
        aria-label="Dismiss hint"
        onclick={onDismiss}
    >
        <X class="h-3.5 w-3.5" />
    </button>
</div>
