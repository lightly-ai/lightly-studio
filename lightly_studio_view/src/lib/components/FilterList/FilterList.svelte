<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Input } from '$lib/components/ui/input';
    import FilterListActions from './FilterListActions.svelte';
    import FilterListRow from './FilterListRow.svelte';
    import { matchesSearch, selectAllVisible, type FilterListItem } from './filterList.helpers';

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
        customRowId = null
    }: Props = $props();

    // Rendering thousands of rows (e.g. a metadata field with a unique value per image) blocks
    // the page for seconds, so long lists render in pages. Search still covers every item.
    const PAGE_SIZE = 50;

    let search = $state('');
    let shownCount = $state(PAGE_SIZE);

    const searchVisible = $derived(showSearch ?? items.length > 5);
    const visible = $derived(items.filter((item) => matchesSearch(item, search)));
    const shown = $derived(visible.slice(0, shownCount));
    const hiddenCount = $derived(visible.length - shown.length);
</script>

<div class="w-full space-y-2 overflow-hidden" data-testid={testId}>
    {#if searchVisible}
        <Input
            value={search}
            oninput={(event) => (search = event.currentTarget.value)}
            placeholder={searchPlaceholder}
            aria-label={searchPlaceholder.replace('…', '')}
            class="h-8"
        />
    {/if}
    {#if items.length > 1}
        <FilterListActions
            onSelectAll={() => onSelectionChange(selectAllVisible(items, visible))}
            onClear={() => onSelectionChange([])}
        />
    {/if}
    {#if pinnedItem && matchesSearch(pinnedItem, search)}
        <FilterListRow
            item={pinnedItem}
            checked={pinnedItem.selected}
            onToggle={pinnedItem.onToggle}
            testId="{testId}-pinned"
            emphasized
        />
    {/if}
    {#each shown as item (item.id)}
        {#if customRow && item.id === customRowId}
            {@render customRow(item)}
        {:else}
            <FilterListRow
                {item}
                checked={item.selected}
                onToggle={() => onToggle(item.id)}
                {testId}
                {leading}
                {trailing}
            />
        {/if}
    {/each}
    {#if hiddenCount > 0}
        <button
            type="button"
            class="text-xs text-diffuse-foreground hover:text-foreground hover:underline"
            onclick={() => (shownCount += PAGE_SIZE)}
        >
            Show {Math.min(PAGE_SIZE, hiddenCount)} more of {hiddenCount}
        </button>
    {/if}
    {#if items.length === 0 && emptyText}
        <p class="text-sm text-diffuse-foreground">{emptyText}</p>
    {:else if items.length > 0 && visible.length === 0}
        <p class="text-sm text-diffuse-foreground">{noMatchText}</p>
    {/if}
</div>
