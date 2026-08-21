<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import TagComparisonSelect from './TagComparisonSelect.svelte';
    import { MultiSelectList } from '$lib/components/MultiSelectList';
    import type { ComponentProps } from 'svelte';

    const { Story } = defineMeta({
        title: 'Components/DatasetDistributionPanel/TagComparisonSelect',
        component: TagComparisonSelect,
        tags: ['autodocs'],
        args: {
            items: [
                { value: 'tag-1', label: 'Train' },
                { value: 'tag-2', label: 'Validation' },
                { value: 'tag-3', label: 'Test' },
                { value: 'tag-4', label: 'Unlabeled' }
            ],
            selectedIds: [],
            onChange: () => {}
        }
    });
</script>

<script lang="ts">
    type MultiSelectItem = ComponentProps<typeof MultiSelectList>['items'];

    const MANY_ITEMS: MultiSelectItem[] = Array.from({ length: 20 }, (_, i) => ({
        value: `tag-${i + 1}`,
        label: `Sample tag ${i + 1}`
    }));

    const LONG_LABELS: MultiSelectItem[] = [
        { value: 'tag-1', label: 'Very long tag name that should be truncated in the trigger' },
        { value: 'tag-2', label: 'Another extremely long sample tag label for testing purposes' },
        { value: 'tag-3', label: 'Short' }
    ];
</script>

<Story name="Empty (no selection)" />

<Story name="One selected" args={{ selectedIds: ['tag-1'] }} />

<Story name="Multiple selected" args={{ selectedIds: ['tag-1', 'tag-2', 'tag-3'] }} />

<Story name="No items" args={{ items: [] }} />

<Story name="Many items (scroll)" args={{ items: MANY_ITEMS }} />

<Story name="Long labels" args={{ items: LONG_LABELS }} />
