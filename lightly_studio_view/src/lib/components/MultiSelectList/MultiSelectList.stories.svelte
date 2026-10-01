<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import MultiSelectList from './MultiSelectList.svelte';

    const { Story } = defineMeta({
        title: 'Components/MultiSelectList',
        component: MultiSelectList,
        tags: ['autodocs'],
        args: {
            items: [
                { value: 'cat', label: 'Cat' },
                { value: 'dog', label: 'Dog' },
                { value: 'bird', label: 'Bird' },
                { value: 'horse', label: 'Horse' },
                { value: 'fish', label: 'Fish' }
            ],
            selectedIds: [],
            onChange: () => {}
        }
    });
</script>

<script lang="ts">
    const manyItems = Array.from({ length: 30 }, (_, i) => ({
        value: `item-${i + 1}`,
        label: `Item ${i + 1}`
    }));

    let selectedIds = $state<string[]>([]);
    let selectedIdsWithCat = $state<string[]>(['cat', 'bird']);
    let selectedIdsWithSelectAll = $state<string[]>(['cat']);
    let allSelected = $state<string[]>(['cat', 'dog', 'bird', 'horse', 'fish']);
    let customNounSelected = $state<string[]>([]);
    let manySelected = $state<string[]>([]);
</script>

<Story name="Empty (no selection)">
    <MultiSelectList
        items={[
            { value: 'cat', label: 'Cat' },
            { value: 'dog', label: 'Dog' },
            { value: 'bird', label: 'Bird' },
            { value: 'horse', label: 'Horse' },
            { value: 'fish', label: 'Fish' }
        ]}
        {selectedIds}
        onChange={(ids) => (selectedIds = ids)}
    />
</Story>

<Story name="With selection">
    <MultiSelectList
        items={[
            { value: 'cat', label: 'Cat' },
            { value: 'dog', label: 'Dog' },
            { value: 'bird', label: 'Bird' },
            { value: 'horse', label: 'Horse' },
            { value: 'fish', label: 'Fish' }
        ]}
        selectedIds={selectedIdsWithCat}
        onChange={(ids) => (selectedIdsWithCat = ids)}
    />
</Story>

<Story name="With select all / clear">
    <MultiSelectList
        items={[
            { value: 'cat', label: 'Cat' },
            { value: 'dog', label: 'Dog' },
            { value: 'bird', label: 'Bird' },
            { value: 'horse', label: 'Horse' },
            { value: 'fish', label: 'Fish' }
        ]}
        selectedIds={selectedIdsWithSelectAll}
        onChange={(ids) => (selectedIdsWithSelectAll = ids)}
        showSelectAll
    />
</Story>

<Story name="All selected">
    <MultiSelectList
        items={[
            { value: 'cat', label: 'Cat' },
            { value: 'dog', label: 'Dog' },
            { value: 'bird', label: 'Bird' },
            { value: 'horse', label: 'Horse' },
            { value: 'fish', label: 'Fish' }
        ]}
        selectedIds={allSelected}
        onChange={(ids) => (allSelected = ids)}
        showSelectAll
    />
</Story>

<Story name="Custom noun">
    <MultiSelectList
        items={[
            { value: 'cat', label: 'Cat' },
            { value: 'dog', label: 'Dog' },
            { value: 'bird', label: 'Bird' },
            { value: 'horse', label: 'Horse' },
            { value: 'fish', label: 'Fish' }
        ]}
        selectedIds={customNounSelected}
        onChange={(ids) => (customNounSelected = ids)}
        itemNoun="tag"
        itemNounPlural="tags"
        showSelectAll
    />
</Story>

<Story name="Many items (scroll)">
    <MultiSelectList
        items={manyItems}
        selectedIds={manySelected}
        onChange={(ids) => (manySelected = ids)}
        showSelectAll
    />
</Story>

<Story name="No items" args={{ items: [] }} />
