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
    import type { ChartSeries } from './types';

    // Two tags overlaid on a categorical key (grouped bars).
    const compareSeries: ChartSeries[] = [
        {
            id: 'current',
            label: 'Current',
            data: [
                { label: 'sunny', count: 40 },
                { label: 'rainy', count: 12 },
                { label: 'foggy', count: 5 },
                { label: '(none)', count: 3 }
            ]
        },
        {
            id: 'night',
            label: 'Night shift',
            data: [
                { label: 'sunny', count: 4 },
                { label: 'rainy', count: 18 },
                { label: 'foggy', count: 20 },
                { label: '(none)', count: 1 }
            ]
        }
    ];

    // A single numeric histogram (filled bars).
    const histogramSingle: ChartSeries[] = [
        {
            id: 'current',
            label: 'Current',
            data: [
                { label: '0–10', count: 4 },
                { label: '10–20', count: 11 },
                { label: '20–30', count: 22 },
                { label: '30–40', count: 14 },
                { label: '40–50', count: 6 },
                { label: '(none)', count: 2 }
            ]
        }
    ];

    // Three tags overlaid on a numeric key (step density curves).
    const histogramCompare: ChartSeries[] = [
        histogramSingle[0],
        {
            id: 'tag-a',
            label: 'Highway',
            data: [
                { label: '0–10', count: 1 },
                { label: '10–20', count: 3 },
                { label: '20–30', count: 9 },
                { label: '30–40', count: 24 },
                { label: '40–50', count: 18 },
                { label: '(none)', count: 0 }
            ]
        },
        {
            id: 'tag-b',
            label: 'City',
            data: [
                { label: '0–10', count: 20 },
                { label: '10–20', count: 15 },
                { label: '20–30', count: 6 },
                { label: '30–40', count: 2 },
                { label: '40–50', count: 0 },
                { label: '(none)', count: 3 }
            ]
        }
    ];
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

<Story name="Compare tags (grouped bars)" args={{ series: compareSeries }} />

<Story
    name="Compare tags (grouped bars, %)"
    args={{ series: compareSeries, normalize: 'percentage' }}
/>

<Story name="Histogram (single series)" args={{ series: histogramSingle, mode: 'histogram' }} />

<Story
    name="Histogram compare (density curves, %)"
    args={{ series: histogramCompare, mode: 'histogram', normalize: 'percentage' }}
/>
