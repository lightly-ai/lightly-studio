<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import BarChart from './BarChart.svelte';

    // Shared across all stories: clicking a bar logs the category in the Actions panel.
    const { Story } = defineMeta({
        title: 'Components/BarChart',
        component: BarChart,
        tags: ['autodocs'],
        args: { onBarClick: fn() }
    });
</script>

<script lang="ts">
    import { balanced, empty, longLabels, longTail, many80Classes, singleClass } from './fixtures';
</script>

<Story name="Balanced (5 classes)" args={{ data: balanced }} />

<Story name="Long-tail imbalance (30 classes)" args={{ data: longTail }} />

<Story name="Many classes (80, horizontal scroll)" args={{ data: many80Classes }} />

<Story name="Long labels (truncation)" args={{ data: longLabels }} />

<Story name="Single class" args={{ data: singleClass }} />

<Story name="Empty" args={{ data: empty }} />

<Story name="Horizontal (5 classes)" args={{ data: balanced, orientation: 'horizontal' }} />

<Story
    name="Horizontal long-tail (30 classes, vertical scroll)"
    args={{ data: longTail, orientation: 'horizontal' }}
/>

<Story name="Horizontal long labels" args={{ data: longLabels, orientation: 'horizontal' }} />
