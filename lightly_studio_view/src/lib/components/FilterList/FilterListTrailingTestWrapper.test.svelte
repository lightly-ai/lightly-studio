<script lang="ts">
    import FilterList from './FilterList.svelte';
    import type { FilterListItem } from './filterList.helpers';

    interface Props {
        items: FilterListItem[];
        pinnedItem: FilterListItem & { onToggle: () => void };
    }

    const { items, pinnedItem }: Props = $props();
</script>

<FilterList {items} {pinnedItem} onToggle={() => {}} onSelectionChange={() => {}}>
    {#snippet trailing(item)}
        <span data-testid="trailing-{item.id}">eye</span>
    {/snippet}
</FilterList>
