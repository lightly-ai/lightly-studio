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
    import type { MultiSelectItem } from './MultiSelectList.svelte';

    const MANY_ITEMS: MultiSelectItem[] = Array.from({ length: 30 }, (_, i) => ({
        value: `item-${i + 1}`,
        label: `Item ${i + 1}`
    }));
</script>

<Story name="Empty (no selection)" />

<Story name="With selection" args={{ selectedIds: ['cat', 'bird'] }} />

<Story name="With select all / clear" args={{ selectedIds: ['cat'], showSelectAll: true }} />

<Story
    name="All selected"
    args={{ selectedIds: ['cat', 'dog', 'bird', 'horse', 'fish'], showSelectAll: true }}
/>

<Story name="Custom noun" args={{ itemNoun: 'tag', itemNounPlural: 'tags', showSelectAll: true }} />

<Story name="Many items (scroll)" args={{ items: MANY_ITEMS, showSelectAll: true }} />

<Story name="No items" args={{ items: [] }} />
