<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import CombinedConfusionMatrix from './CombinedConfusionMatrix.svelte';

    const { Story } = defineMeta({
        title: 'Prototypes/ConfusionMatrix LIG-9665',
        component: CombinedConfusionMatrix,
        args: { topN: 5, classCountThreshold: 30, showLegend: true },
        argTypes: {
            topN: { control: { type: 'number', min: 1, max: 80, step: 1 } },
            classCountThreshold: { control: { type: 'number', min: 0, max: 80, step: 1 } }
        }
    });
</script>

<script lang="ts">
    import { coco80Classes } from '../fixtures';
</script>

<!--
Combined flow: comma-separated class filter with typed suggestions on top;
otherwise top-N most confused classes + "(other)" aggregation.
-->
<Story name="Large (80 classes, filter + top-N)">
    {#snippet template(args)}
        <CombinedConfusionMatrix {...args} matrix={coco80Classes} />
    {/snippet}
</Story>
