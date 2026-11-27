<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import NumericRangeInputs from './NumericRangeInputs.svelte';

    const { Story } = defineMeta({
        title: 'Components/NumericRangeInputs',
        component: NumericRangeInputs
    });
</script>

<script lang="ts">
    let value = $state({ min: 257, max: 800 });
</script>

<Story name="Width" asChild>
    <div class="w-64">
        <NumericRangeInputs
            label="Width"
            bound={{ min: 0, max: 1000 }}
            {value}
            integer
            unit="px"
            onValueCommit={([min, max]) => (value = { min, max })}
        />
    </div>
</Story>
