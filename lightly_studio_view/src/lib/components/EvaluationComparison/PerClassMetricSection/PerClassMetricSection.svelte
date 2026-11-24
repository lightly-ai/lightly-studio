<script lang="ts">
    import * as Tabs from '$lib/components/ui/tabs';
    import {
        PER_CLASS_METRIC_LABELS,
        perClassMetrics,
        perClassRows,
        type ComparableTaskType,
        type ComparedRun,
        type PerClassMetric
    } from '../EvaluationComparison.helpers';
    import PerClassMetricChart from './PerClassMetricChart/PerClassMetricChart.svelte';
    import PerClassMetricTable from './PerClassMetricTable/PerClassMetricTable.svelte';

    interface Props {
        taskType: ComparableTaskType;
        runs: ComparedRun[];
    }

    const { taskType, runs }: Props = $props();

    const metrics = $derived(perClassMetrics(taskType));
    let selectedMetric = $state<string>('');
    const activeMetric: PerClassMetric = $derived(
        metrics.find((metric) => metric === selectedMetric) ?? metrics[0]
    );
    const rows = $derived(perClassRows(runs, activeMetric));
</script>

<section class="flex flex-col gap-3" data-testid="per-class-metrics">
    <div class="flex items-center justify-between">
        <h2 class="text-base font-semibold">Per annotation class</h2>
        <Tabs.Root value={activeMetric} onValueChange={(value) => (selectedMetric = value)}>
            <Tabs.List>
                {#each metrics as metric (metric)}
                    <Tabs.Trigger value={metric}>{PER_CLASS_METRIC_LABELS[metric]}</Tabs.Trigger>
                {/each}
            </Tabs.List>
        </Tabs.Root>
    </div>
    <PerClassMetricChart {runs} {rows} />
    <PerClassMetricTable runNames={runs.map((entry) => entry.run.name)} {rows} />
</section>
