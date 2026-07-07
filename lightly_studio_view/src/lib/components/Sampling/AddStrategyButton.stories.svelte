<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import AddStrategyButton from './AddStrategyButton.svelte';

    const { Story } = defineMeta({
        title: 'Components/Sampling/AddStrategyButton',
        component: AddStrategyButton,
        tags: ['autodocs'],
        parameters: {
            layout: 'centered'
        },
        argTypes: {
            similarityDisabledReason: { control: 'text' },
            metadataWeightingDisabledReason: { control: 'text' },
            classBalancingDisabledReason: { control: 'text' }
        }
    });
</script>

<Story name="Default" args={{ onAdd: fn() }}>
    {#snippet children({ args })}
        <div style="width: 300px">
            <AddStrategyButton {...args} />
        </div>
    {/snippet}
</Story>

<Story
    name="SimilarityDisabled"
    args={{
        similarityDisabledReason: 'No query tag selected',
        onAdd: fn()
    }}
>
    {#snippet children({ args })}
        <div style="width: 300px">
            <AddStrategyButton {...args} />
        </div>
    {/snippet}
</Story>

<Story
    name="AllDisabled"
    args={{
        similarityDisabledReason: 'No query tag selected',
        metadataWeightingDisabledReason: 'No numeric metadata available',
        classBalancingDisabledReason: 'No annotations available',
        onAdd: fn()
    }}
>
    {#snippet children({ args })}
        <div style="width: 300px">
            <AddStrategyButton {...args} />
        </div>
    {/snippet}
</Story>
