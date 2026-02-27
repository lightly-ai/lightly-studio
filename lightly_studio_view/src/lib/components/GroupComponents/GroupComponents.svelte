<script lang="ts">
    import LayoutCard from '../LayoutCard/LayoutCard.svelte';
    import type { Snippet } from 'svelte';

    let {
        itemsCount,
        selectedIndex = -1,
        onclick,
        renderItem
    }: {
        itemsCount: number;
        selectedIndex?: number;
        onclick?: (index: number) => void;
        renderItem: Snippet<[{ index: number }]>;
    } = $props();
</script>

<LayoutCard>
    <div class="flex w-[200px] flex-col gap-4 p-4">
        {#each Array(itemsCount) as _, index}
            <div
                class="image-item overflow-hidden {index === selectedIndex
                    ? 'selected'
                    : 'opacity-50'}"
                role="button"
                tabindex="0"
                onclick={() => onclick?.(index)}
                onkeydown={(e) => e.key === 'Enter' && onclick?.(index)}
            >
                {@render renderItem({ index })}
            </div>
        {/each}
    </div>
</LayoutCard>

<style>
    .selected {
        @apply rounded opacity-100 outline outline-4 outline-offset-2 outline-primary/80;
    }

    .image-item :global(img) {
        @apply transition-transform duration-300 ease-in-out;
    }

    .image-item:hover :global(img) {
        @apply scale-125;
    }
</style>
