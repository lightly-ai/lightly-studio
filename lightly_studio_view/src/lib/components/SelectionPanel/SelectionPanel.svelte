<script lang="ts">
    import { X } from '@lucide/svelte';
    import type { GridType } from '$lib/types';

    interface Props {
        selectedSampleIds: Set<string>;
        gridType: GridType;
        onClear: () => void;
        onSelectAll: () => void | Promise<void>;
        isSelectingAll?: boolean;
    }

    let {
        selectedSampleIds,
        gridType,
        onClear,
        onSelectAll,
        isSelectingAll = false
    }: Props = $props();

    const N = $derived(selectedSampleIds.size);
    const selectionLabel = $derived.by(() => {
        if (gridType === 'annotations') return N === 1 ? 'annotation' : 'annotations';
        if (gridType === 'videos') return N === 1 ? 'video' : 'videos';
        if (gridType === 'video_frames') return N === 1 ? 'frame' : 'frames';
        return N === 1 ? 'image' : 'images';
    });
</script>

<div class="mb-3 rounded-md border border-border bg-card/60 p-3">
    <!-- Header -->
    <div class="mb-2 flex items-center justify-between">
        <span class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {N} {selectionLabel} selected
        </span>
        <div class="flex items-center gap-1">
            {#if N === 0}
                <button
                    type="button"
                    class="rounded px-1.5 py-0.5 text-[10px] text-muted-foreground ring-1 ring-border hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
                    onclick={() => void onSelectAll()}
                    disabled={isSelectingAll}
                >
                    {isSelectingAll ? 'Selecting...' : 'Select all'}
                </button>
            {:else}
                <button
                    type="button"
                    class="rounded p-0.5 text-muted-foreground hover:text-foreground"
                    aria-label="Clear selection"
                    onclick={onClear}
                >
                    <X class="size-3.5" />
                </button>
            {/if}
        </div>
    </div>
</div>
