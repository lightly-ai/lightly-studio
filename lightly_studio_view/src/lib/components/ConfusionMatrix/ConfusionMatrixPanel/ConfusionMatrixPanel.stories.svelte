<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import ConfusionMatrixPanel from './ConfusionMatrixPanel.svelte';

    const { Story } = defineMeta({
        title: 'Components/ConfusionMatrixPanel',
        component: ConfusionMatrixPanel,
        tags: ['autodocs'],
        args: { topN: 5, showLegend: true },
        argTypes: {
            topN: { control: { type: 'number', min: 1, max: 80, step: 1 } }
        }
    });
</script>

<script lang="ts">
    import { coco80Classes } from '../fixtures';
</script>

<Story name="Default">
    {#snippet template(args)}
        <ConfusionMatrixPanel {...args} matrix={coco80Classes} />
    {/snippet}
</Story>
