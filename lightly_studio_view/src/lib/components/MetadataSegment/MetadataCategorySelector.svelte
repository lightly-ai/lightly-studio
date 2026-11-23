<script lang="ts">
    import { MultiSelectPopover } from '$lib/components/MultiSelectPopover';

    interface CategoryItem {
        value: string;
        label: string;
    }

    interface Props {
        items: CategoryItem[];
        selectedIds: string[] | null;
        onChange: (ids: string[]) => void;
    }

    const { items, selectedIds, onChange }: Props = $props();
    const selected = $derived(selectedIds ?? items.map(({ value }) => value));
    const label = $derived(
        selected.length === items.length
            ? 'All categories'
            : `${selected.length} categories selected`
    );
</script>

<MultiSelectPopover
    {items}
    selectedIds={selected}
    {onChange}
    {label}
    itemNoun="category"
    itemNounPlural="categories"
    showSelectAll
    searchTestId="metadata-category-search"
    ariaLabel="Choose metadata categories"
    align="start"
    triggerClass="w-full"
    contentClass="w-[min(320px,calc(100vw-2rem))]"
    testId="metadata-category-select"
/>
