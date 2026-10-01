<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Histogram from './Histogram.svelte';

    const { Story } = defineMeta({
        title: 'Components/Histogram',
        component: Histogram,
        tags: ['autodocs']
    });
</script>

<script lang="ts">
    import { empty, normal, singleBin, skewed } from './fixtures';
</script>

<Story name="Normal distribution" args={{ data: normal }} />

<Story
    name="Range selected (middle)"
    args={{ data: normal, selectedRange: { min: 25, max: 60 } }}
/>

<Story name="Range selected (tail)" args={{ data: skewed, selectedRange: { min: 0, max: 0.2 } }} />

<Story name="Skewed distribution" args={{ data: skewed }} />

<Story name="Single bin (constant values)" args={{ data: singleBin }} />

<Story name="Empty" args={{ data: empty }} />

<Story name="Taller (96px)" args={{ data: normal, heightPx: 96 }} />

<!-- Panel variant: numeric bin-edge values on the x-axis, counts on the y-axis. -->
<Story name="With axes (panel variant)" args={{ data: normal, heightPx: 240, showAxes: true }} />

<Story name="With axes, skewed" args={{ data: skewed, heightPx: 240, showAxes: true }} />
