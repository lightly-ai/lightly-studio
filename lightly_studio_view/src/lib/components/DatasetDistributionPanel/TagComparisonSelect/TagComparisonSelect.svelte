<script lang="ts">
    import { MultiSelectList } from '$lib/components/MultiSelectList';
    import { MultiSelectPopover } from '$lib/components/MultiSelectPopover';
    import type { ComponentProps } from 'svelte';

    interface Props {
        items: ComponentProps<typeof MultiSelectList>['items'];
        selectedIds: string[];
        onChange: (ids: string[]) => void;
    }

    const { items, selectedIds, onChange }: Props = $props();
    const label = $derived(
        selectedIds.length === 0
            ? 'Compare sample tags'
            : `${selectedIds.length} tag${selectedIds.length === 1 ? '' : 's'} selected`
    );
</script>

<MultiSelectPopover
    {items}
    {selectedIds}
    {onChange}
    {label}
    itemNoun="sample tag"
    itemNounPlural="sample tags"
    triggerClass="m-0 flex-1 rounded-md"
    contentClass="w-[260px]"
    testId="dataset-distribution-tag-select"
/>
