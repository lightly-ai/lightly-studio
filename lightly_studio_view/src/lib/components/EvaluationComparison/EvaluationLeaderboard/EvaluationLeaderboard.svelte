<script lang="ts">
    import { Badge } from '$lib/components/ui/badge';
    import {
        AVERAGE_PRECISION_METRICS,
        LEADERBOARD_METRIC_LABELS,
        bestIndices,
        formatMetricValue,
        leaderboardValue,
        type ComparedRun,
        type LeaderboardMetric
    } from '../EvaluationComparison.helpers';

    interface Props {
        /** Runs in display order. */
        runs: ComparedRun[];
        columns: LeaderboardMetric[];
        staleRunIds: string[];
    }

    const { runs, columns, staleRunIds }: Props = $props();

    const valuesByColumn = $derived(
        columns.map((column) => runs.map((entry) => leaderboardValue(entry.metrics, column)))
    );
    const bestByColumn = $derived(valuesByColumn.map((values) => bestIndices(values)));

    const missingHint = (column: LeaderboardMetric, value: number | null): string | undefined =>
        value === null && AVERAGE_PRECISION_METRICS.includes(column)
            ? 'Recompute with average precision'
            : undefined;
</script>

<table class="w-full text-sm" data-testid="evaluation-leaderboard">
    <thead>
        <tr class="border-b text-left text-muted-foreground">
            <th class="py-2 pr-4 font-medium">Run</th>
            {#each columns as column (column)}
                <th class="px-3 py-2 text-right font-medium">{LEADERBOARD_METRIC_LABELS[column]}</th
                >
            {/each}
        </tr>
    </thead>
    <tbody>
        {#each runs as entry, runIndex (entry.run.id)}
            <tr class="border-b">
                <td class="py-2 pr-4">
                    <div class="flex items-center gap-2 font-medium">
                        {entry.run.name}
                        {#if staleRunIds.includes(entry.run.id)}
                            <Badge variant="outline">Stale</Badge>
                        {/if}
                    </div>
                    <div class="text-xs text-muted-foreground">
                        {entry.run.gt_annotation_source} vs {entry.run.pred_annotation_source}
                    </div>
                </td>
                {#each columns as column, columnIndex (column)}
                    {@const value = valuesByColumn[columnIndex][runIndex]}
                    {@const isBest = bestByColumn[columnIndex].includes(runIndex)}
                    <td
                        class="px-3 py-2 text-right tabular-nums"
                        class:font-semibold={isBest}
                        data-best={isBest}
                        title={missingHint(column, value)}
                    >
                        {formatMetricValue(value)}
                    </td>
                {/each}
            </tr>
        {/each}
    </tbody>
</table>
