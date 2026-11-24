<script lang="ts">
    import {
        perClassChartSeries,
        type ComparedRun,
        type PerClassRow
    } from '../../EvaluationComparison.helpers';

    interface Props {
        runs: ComparedRun[];
        rows: PerClassRow[];
    }

    const { runs, rows }: Props = $props();

    const categories = $derived(rows.map((row) => ({ label: row.label, count: 0 })));
    const series = $derived(perClassChartSeries(runs, rows));
</script>

{#await import('$lib/components/BarChart/BarChart.svelte') then { default: BarChart }}
    <BarChart data={categories} {series} maxHeightPx={320} />
{/await}
