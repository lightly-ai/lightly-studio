<script lang="ts">
    import { formatMetricValue, type PerClassRow } from '../../EvaluationComparison.helpers';

    interface Props {
        runNames: string[];
        rows: PerClassRow[];
    }

    const { runNames, rows }: Props = $props();
</script>

<div class="max-h-[480px] overflow-y-auto rounded-md border" data-testid="per-class-metric-table">
    <table class="w-full text-sm">
        <thead>
            <tr class="text-left text-muted-foreground">
                <th class="sticky top-0 z-10 border-b bg-background py-2 pl-3 pr-4 font-medium">
                    Annotation class
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
            {#each rows as row (row.label)}
                <tr class="border-b last:border-b-0">
                    <td class="py-2 pl-3 pr-4">{row.label}</td>
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
