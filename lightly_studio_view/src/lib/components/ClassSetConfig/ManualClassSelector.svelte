<script lang="ts">
    import { MultiSelectList } from '$lib/components/MultiSelectList';
    import type { MultiSelectItem } from '$lib/components/MultiSelectList';

    interface Props {
        /** Currently selected class labels. Bindable — mutated on toggle / Select all / Clear. */
        selected: string[];
        /** Full list of class labels to choose from, in the order they should be displayed. */
        allClasses?: string[];
        /** Optional stable values and display labels; labels need not be unique. */
        items?: MultiSelectItem[];
        itemNoun?: string;
        itemNounPlural?: string;
        /** test-id for the search input; lets each host keep its own id scheme. */
        searchTestId?: string;
    }

    let {
        selected = $bindable(),
        allClasses,
        items,
        itemNoun = 'class',
        itemNounPlural = 'classes',
        searchTestId
    }: Props = $props();

    const resolvedItems = $derived(
        items ?? (allClasses ?? []).map((className) => ({ value: className, label: className }))
    );
</script>

<div class="pt-2">
    <MultiSelectList
        items={resolvedItems}
        selectedIds={selected}
        onChange={(ids) => (selected = ids)}
        showSelectAll
        {itemNoun}
        {itemNounPlural}
        {searchTestId}
    />
</div>
