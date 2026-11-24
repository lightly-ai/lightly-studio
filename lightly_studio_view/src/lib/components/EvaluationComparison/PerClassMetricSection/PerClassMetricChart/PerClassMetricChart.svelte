<script lang="ts">
    import type { CategoryCountSeries } from '$lib/components/BarChart';
    import type { ComparedRun, PerClassRow } from '../../EvaluationComparison.helpers';

    interface Props {
        runs: ComparedRun[];
        rows: PerClassRow[];
    }

    const { runs, rows }: Props = $props();

    // The bar chart shows whole numbers best, so values show as percentage points.
    const PERCENT = 100;
    const toPercentPoints = (value: number): number => Math.round(value * PERCENT * 10) / 10;

    const categories = $derived(rows.map((row) => ({ label: row.label, count: 0 })));
    const series: CategoryCountSeries[] = $derived(
        runs.map((entry, runIndex) => ({
            id: entry.run.id,
            label: entry.run.name,
            data: rows.flatMap((row) => {
                const value = row.values[runIndex];
                return value === null ? [] : [{ label: row.label, count: toPercentPoints(value) }];
            })
        }))
    );
</script>

{#await import('$lib/components/BarChart/BarChart.svelte') then { default: BarChart }}
    <BarChart data={categories} {series} maxHeightPx={320} />
{/await}
