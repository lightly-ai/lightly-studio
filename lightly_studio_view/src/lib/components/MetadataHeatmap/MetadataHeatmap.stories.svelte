<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import MetadataHeatmap from './MetadataHeatmap.svelte';

    const { Story } = defineMeta({
        title: 'Components/MetadataHeatmap',
        component: MetadataHeatmap,
        tags: ['autodocs']
    });
</script>

<script lang="ts">
    const months = ['January', 'February', 'March', 'April', 'May', 'June'];
    const monthByYear = {
        xAxis: { name: 'month', labels: months },
        yAxis: { name: 'year', labels: ['2025', '2026', '2027'] },
        counts: [
            [12, 30, 8, 41, 0, 5],
            [3, 18, 22, 9, 14, 27],
            [0, 2, 6, 11, 1, 0]
        ],
        heightPx: 240
    };
</script>

<Story name="Month by year" args={{ ...monthByYear, selection: null }} />

<Story name="One cell selected" args={{ ...monthByYear, selection: { x: [3], y: [0] } }} />

<Story name="Column selected" args={{ ...monthByYear, selection: { x: [1, 2], y: null } }} />
