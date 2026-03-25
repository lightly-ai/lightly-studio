<script lang="ts">
    import { Image as ImageIcon, X } from '@lucide/svelte';

    interface Props {
        activeImage: string | null;
        submittedQueryText: string;
        previewUrl: string | null;
        dragOver: boolean;
        onClearImage: () => void;
        onClearText: () => void;
    }

    let {
        activeImage,
        submittedQueryText,
        previewUrl,
        dragOver,
        onClearImage,
        onClearText
    }: Props = $props();
</script>

<div
    class="flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 pl-8 text-sm {dragOver
        ? 'ring-2 ring-primary'
        : ''}"
>
    {#if activeImage}
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
            onclick={onClearImage}
            title="Clear search"
            data-testid="search-clear-button"
        >
            <X class="h-4 w-4" />
        </button>
    {:else}
        <button
            type="button"
            class="mr-2 min-w-0 flex-1 cursor-text truncate text-left text-muted-foreground"
            onclick={onClearText}
        >
            {submittedQueryText}
        </button>
        <button
            class="ml-auto hover:text-foreground"
            onclick={onClearImage}
            title="Clear search"
            data-testid="search-clear-button"
        >
            <X class="h-4 w-4" />
        </button>
    {/if}
</div>
