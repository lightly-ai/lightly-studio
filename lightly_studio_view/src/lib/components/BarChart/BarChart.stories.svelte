<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import BarChart from './BarChart.svelte';

    const { Story } = defineMeta({
        title: 'Components/BarChart',
        component: BarChart,
        tags: ['autodocs']
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
