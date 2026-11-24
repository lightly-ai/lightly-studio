<script lang="ts">
    import { formatMetricValue, type ScenarioRow } from '../../EvaluationComparison.helpers';

    interface Props {
        runNames: string[];
        rows: ScenarioRow[];
    }

    const { runNames, rows }: Props = $props();

    const imageCountText = (row: ScenarioRow): string =>
        new Set(row.sampleCounts).size > 1
            ? 'different images'
            : `${row.sampleCounts[0] ?? 0} images`;
</script>

<div class="max-h-[480px] overflow-y-auto rounded-md border" data-testid="scenario-table">
    <table class="w-full text-sm">
        <thead>
            <tr class="text-left text-muted-foreground">
                <th class="sticky top-0 z-10 border-b bg-background py-2 pl-3 pr-4 font-medium">
                    Scenario
                </th>
                {#each runNames as runName, index (index)}
                    <th
                        class="sticky top-0 z-10 border-b bg-background px-3 py-2 text-right font-medium"
                    >
                        {runName}
                    </th>
                {/each}
            </tr>
        </thead>
        <tbody>
            {#each rows as row (row.id)}
                <tr class="border-b last:border-b-0">
                    <td class="py-2 pl-3 pr-4">
                        <div>{row.label}</div>
                        <div class="text-xs text-muted-foreground">{imageCountText(row)}</div>
                    </td>
                    {#each row.values as value, index (index)}
                        {@const isBest = row.bestIndices.includes(index)}
                        <td
                            class="px-3 py-2 text-right tabular-nums"
                            class:font-semibold={isBest}
                            data-best={isBest}
                        >
                            {formatMetricValue(value)}
                        </td>
                    {/each}
                </tr>
            {/each}
        </tbody>
    </table>
</div>
