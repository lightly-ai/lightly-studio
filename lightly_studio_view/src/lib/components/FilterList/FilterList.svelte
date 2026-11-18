<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Input } from '$lib/components/ui/input';
    import { cn } from '$lib/utils';
    import FilterListActions from './FilterListActions/FilterListActions.svelte';
    import FilterListRows from './FilterListRows/FilterListRows.svelte';
    import { matchesSearch, selectAllMatching, type FilterListItem } from './filterList.helpers';
    import { useFilterListState } from './useFilterListState/useFilterListState.svelte';

    interface Props {
        /** The values to filter by, in display order. */
        items: FilterListItem[];
        /** Toggles one value in the applied selection. */
        onToggle: (id: string) => void;
        /** Replaces the applied selection; used by "Select all" and "Clear". */
        onSelectionChange: (ids: string[]) => void;
        /** A special row above the list, e.g. "No annotations". Not part of the selection. */
        pinnedItem?: FilterListItem & { onToggle: () => void };
        /** Prefix of the row test ids: `{testId}-item`, `{testId}-name`, `{testId}-count`. */
        testId?: string;
        /** Whether to show the search box. Defaults to more than five items. */
        showSearch?: boolean;
        searchPlaceholder?: string;
        /** Shown when there are no items at all. */
        emptyText?: string;
        /** Shown when the search matches no item. */
        noMatchText?: string;
        /** Renders before the label of each row, e.g. a color marker. */
        leading?: Snippet<[FilterListItem]>;
        /** Renders after the row, e.g. a visibility toggle or an action menu. */
        trailing?: Snippet<[FilterListItem]>;
        /** Renders instead of the row whose id is `customRowId`, e.g. a rename input. */
        customRow?: Snippet<[FilterListItem]>;
        customRowId?: string | null;
        /** Whether long lists render in pages of 50 rows. Turn off for short lists like tags. */
        paged?: boolean;
        /** Classes of the box around the rows, e.g. a max height so only the rows scroll. */
        rowsClass?: string;
    }

    const {
        items,
        onToggle,
        onSelectionChange,
        pinnedItem,
        testId = 'filter-list',
        showSearch,
        searchPlaceholder = 'Search…',
        emptyText,
        noMatchText = 'No matches.',
        leading,
        trailing,
        customRow,
        customRowId = null,
        paged = true,
        rowsClass
    }: Props = $props();

    const list = useFilterListState({
        getItems: () => items,
        getShowSearch: () => showSearch,
        getPaged: () => paged
    });
    const pinnedVisible = $derived(!!pinnedItem && matchesSearch(pinnedItem, list.search));
</script>

<div class="w-full min-w-0 space-y-2" data-testid={testId}>
    {#if list.searchVisible}
        <Input
            value={list.search}
            oninput={(event) => list.setSearch(event.currentTarget.value)}
            placeholder={searchPlaceholder}
            aria-label={searchPlaceholder.replace('…', '')}
            class="h-8"
        />
    {/if}
    {#if items.length > 1}
        <FilterListActions
            onSelectAll={() => onSelectionChange(selectAllMatching(items, list.matching))}
            onClear={() => onSelectionChange([])}
        />
    {/if}
    {#snippet rows()}
        <FilterListRows
            items={list.shown}
            onToggle={(id) => {
                list.keep(id);
                onToggle(id);
            }}
            pinnedItem={pinnedVisible ? pinnedItem : undefined}
            search={list.search}
            {testId}
            nextPageCount={list.nextPageCount}
            onShowMore={list.showMore}
            {leading}
            {trailing}
            {customRow}
            {customRowId}
        />
    {/snippet}
    {#if rowsClass}
        <div class={cn('space-y-2', rowsClass)}>{@render rows()}</div>
    {:else}
        {@render rows()}
    {/if}
    {#if items.length === 0 && emptyText}
        <p class="text-sm text-diffuse-foreground">{emptyText}</p>
    {:else if items.length > 0 && list.matching.length === 0 && !pinnedVisible}
        <p class="text-sm text-diffuse-foreground">{noMatchText}</p>
    {/if}
</div>
