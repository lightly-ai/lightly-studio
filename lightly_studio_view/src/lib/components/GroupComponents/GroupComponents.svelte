<script lang="ts">
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

<div class="flex flex-col gap-4">
    {#each Array.from({ length: itemsCount }, (_, index) => index) as index}
        <div
            class="group-item relative overflow-hidden {index === selectedIndex
                ? 'rounded opacity-100 outline outline-2 outline-offset-1 outline-primary/80'
                : 'opacity-50'} "
            role="button"
            tabindex="0"
            onclick={() => onclick?.(index)}
            onkeydown={(e) => e.key === 'Enter' && onclick?.(index)}
        >
            {@render renderItem({ index })}
        </div>
    {/each}
</div>
