<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import CombinedConfusionMatrix from './CombinedConfusionMatrix.svelte';

    const { Story } = defineMeta({
        title: 'Prototypes/ConfusionMatrix LIG-9665',
        component: CombinedConfusionMatrix
    });
</script>

<script lang="ts">
    import { coco80Classes } from '../fixtures';
</script>

<!--
Combined flow: top-N most confused classes + "(other)" aggregation in the panel,
"Full matrix" dialog with comma-separated class filter and inside zoom.
-->
<Story name="Large (80 classes, top-N + dialog)">
    {#snippet template()}
        <CombinedConfusionMatrix matrix={coco80Classes} showLegend />
    {/snippet}
</Story>
