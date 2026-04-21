<!--
  Display-only component for active image search state in `CollectionSearch`.
  It isolates the uploaded image preview/name + clear action so image-mode UI stays
  separate from text-input UI and can be tested/reused independently.
-->
<script lang="ts">
    import { Image as ImageIcon, X } from '@lucide/svelte';
    import { cn } from '$lib/utils';

    interface Props {
        name: string;
        onClear: () => void;
        showOutline?: boolean;
        src?: string;
    }

    let { name, src, showOutline = false, onClear }: Props = $props();
</script>

<div
    class={cn(
        'flex h-10 w-full items-center rounded-md border border-input bg-background px-3 py-2 pl-8 text-sm',
        showOutline && 'ring-2 ring-primary'
    )}
>
    <span class="mr-2 flex min-w-0 flex-1 items-center gap-2 text-muted-foreground">
        {#if src}
            <img {src} alt="Search preview" class="h-6 w-6 shrink-0 rounded object-cover" />
        {:else}
            <ImageIcon class="h-4 w-4 shrink-0" />
        {/if}
        <span class="min-w-0 truncate" title={name}>{name}</span>
    </span>
    <button
        class="ml-auto hover:text-foreground"
        onclick={onClear}
        title="Clear search"
        type="button"
        data-testid="search-clear-button"
    >
        <X class="h-4 w-4" />
    </button>
</div>
