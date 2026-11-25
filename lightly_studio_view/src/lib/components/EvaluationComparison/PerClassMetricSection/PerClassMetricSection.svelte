<script lang="ts">
    import * as Tabs from '$lib/components/ui/tabs';
    import {
        DEFAULT_CLASS_LIMIT,
        PER_CLASS_METRIC_LABELS,
        perClassMetrics,
        perClassRows,
        topClassesByGap,
        type ClassLimit,
        type ComparableTaskType,
        type ComparedRun,
        type PerClassMetric,
        type PerClassView
    } from '../EvaluationComparison.helpers';
    import PerClassMetricChart from './PerClassMetricChart/PerClassMetricChart.svelte';
    import PerClassMetricTable from './PerClassMetricTable/PerClassMetricTable.svelte';
    import PerClassViewControls from './PerClassViewControls/PerClassViewControls.svelte';

    interface Props {
        taskType: ComparableTaskType;
        runs: ComparedRun[];
    }

    const { taskType, runs }: Props = $props();

    const metrics = $derived(perClassMetrics(taskType));
    let selectedMetric = $state<string>('');
    let view = $state<PerClassView>('bar_chart');
    let classLimit = $state<ClassLimit>(DEFAULT_CLASS_LIMIT);
    const activeMetric: PerClassMetric = $derived(
        metrics.find((metric) => metric === selectedMetric) ?? metrics[0]
    );
    const allRows = $derived(perClassRows(runs, activeMetric));
    const rows = $derived(topClassesByGap(allRows, classLimit));
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
    <PerClassViewControls
        {view}
        onViewChange={(selectedView) => (view = selectedView)}
        {classLimit}
        onClassLimitChange={(selectedLimit) => (classLimit = selectedLimit)}
        shownClassCount={rows.length}
        totalClassCount={allRows.length}
    />
    {#if view === 'bar_chart'}
        <PerClassMetricChart {runs} {rows} />
    {:else}
        <PerClassMetricTable runNames={runs.map((entry) => entry.run.name)} {rows} />
    {/if}
</section>
