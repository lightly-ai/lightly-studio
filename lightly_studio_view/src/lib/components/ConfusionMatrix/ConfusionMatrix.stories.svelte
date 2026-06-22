<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import ConfusionMatrix from './ConfusionMatrix.svelte';

    const { Story } = defineMeta({
        title: 'Components/ConfusionMatrix',
        component: ConfusionMatrix,
        tags: ['autodocs']
    });
</script>

<script lang="ts">
    import CombinedConfusionMatrix from './CombinedConfusionMatrix.svelte';
    import {
        coco80Classes,
        empty,
        large20Classes,
        medium8Classes,
        singleClass,
        small3Classes
    } from './fixtures';
</script>

<Story name="Small (3 classes)" args={{ matrix: small3Classes }} />

<Story name="Medium (8 classes)" args={{ matrix: medium8Classes }} />

<Story name="Large (20 classes)" args={{ matrix: large20Classes }} />

<Story name="Empty" args={{ matrix: empty }} />

<Story name="Single class" args={{ matrix: singleClass }} />

<Story name="With legend" args={{ matrix: medium8Classes, showLegend: true }} />

<!--
  CombinedConfusionMatrix: shows the full matrix for small class counts and
  switches to top-N + "(other)" aggregation for large ones.
-->
<Story name="Combined — large (80 classes, top-N)">
    {#snippet template(args)}
        <CombinedConfusionMatrix {...args} matrix={coco80Classes} showLegend={true} />
    {/snippet}
</Story>
