<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import MetadataFilterItem from './MetadataFilterItem.svelte';

    const { Story } = defineMeta({
        title: 'Components/MetadataFilterItem',
        component: MetadataFilterItem
    });
</script>

<script lang="ts">
    let value = $state({ min: 0.123456789, max: 0.876543219 });
</script>

<Story name="Exact decimals" asChild>
    <div class="w-64">
        <MetadataFilterItem
            metadataKey="confidence"
            bound={{ min: 0, max: 1 }}
            {value}
            isInteger={false}
            onValueCommit={(_, [min, max]) => (value = { min, max })}
        />
    </div>
</Story>
