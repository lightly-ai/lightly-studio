<!--
  Display-only component for active image search state in `CollectionSearch`.
  It isolates the uploaded image preview/name + clear action so image-mode UI stays
  separate from text-input UI and can be tested/reused independently.
-->
<script lang="ts">
    import { Image as ImageIcon, X } from '@lucide/svelte';

    type Props = {
        activeImage: string;
        previewUrl: string | null;
        dragOver: boolean;
        onClear: () => void;
    };

    let { activeImage, previewUrl, dragOver, onClear }: Props = $props();
</script>

<div
    class="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 pl-8 text-sm {dragOver
        ? 'ring-2 ring-primary'
        : ''}"
>
    <span class="mr-2 flex items-center gap-2 truncate text-muted-foreground">
        {#if previewUrl}
            <img src={previewUrl} alt="Search preview" class="h-6 w-6 rounded object-cover" />
        {:else}
            <ImageIcon class="h-4 w-4" />
        {/if}
        {activeImage}
    </span>
    <button
        class="ml-auto hover:text-foreground"
        onclick={onClear}
        title="Clear search"
        data-testid="search-clear-button"
    >
        <X class="h-4 w-4" />
    </button>
</div>
