<script lang="ts">
    import type { Snippet } from 'svelte';
    import { ChevronDown } from '@lucide/svelte';
    import { FilterActionButton } from '$lib/components/FilterActionButton';
    import FilterListRow from './FilterListRow.svelte';
    import { highlightRange, type FilterListItem } from './filterList.helpers';

    interface Props {
        /** The rows of the current page. */
        items: FilterListItem[];
        onToggle: (id: string) => void;
        pinnedItem?: FilterListItem & { onToggle: () => void };
        search: string;
        testId: string;
        /** Number of rows "Show more" adds. Hides the button when 0. */
        nextPageCount: number;
        onShowMore: () => void;
        leading?: Snippet<[FilterListItem]>;
        trailing?: Snippet<[FilterListItem]>;
        customRow?: Snippet<[FilterListItem]>;
        customRowId: string | null;
    }

    const {
        items,
        onToggle,
        pinnedItem,
        search,
        testId,
        nextPageCount,
        onShowMore,
        leading,
        trailing,
        customRow,
        customRowId
    }: Props = $props();
</script>

{#if pinnedItem}
    <FilterListRow
        item={pinnedItem}
        checked={pinnedItem.selected}
        onToggle={pinnedItem.onToggle}
        testId="{testId}-pinned"
        highlight={highlightRange(pinnedItem.label, search)}
        emphasized
        trailingSpacer={trailing}
    />
{/if}
{#each items as item (item.id)}
    {#if customRow && item.id === customRowId}
        {@render customRow(item)}
    {:else}
        <FilterListRow
            {item}
            checked={item.selected}
            onToggle={() => onToggle(item.id)}
            {testId}
            highlight={highlightRange(item.label, search)}
            {leading}
            {trailing}
        />
    {/if}
{/each}
{#if nextPageCount > 0}
    <FilterActionButton label="Show {nextPageCount} more" icon={ChevronDown} onclick={onShowMore} />
{/if}
