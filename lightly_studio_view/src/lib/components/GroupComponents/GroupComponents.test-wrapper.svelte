<script lang="ts">
    import GroupComponents from './GroupComponents.svelte';

    let {
        itemsCount,
        selectedIndex = -1,
        onclick
    }: {
        itemsCount: number;
        selectedIndex?: number;
        onclick?: (index: number) => void;
    } = $props();
</script>

<GroupComponents {itemsCount} {selectedIndex} {onclick}>
    {#snippet renderItem({ index })}
        Item {index}
    {/snippet}
</GroupComponents>
