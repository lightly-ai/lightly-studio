<script lang="ts">
    import ComparabilityWarning from '../ComparabilityWarning/ComparabilityWarning.svelte';
    import EvaluationLeaderboard from '../EvaluationLeaderboard/EvaluationLeaderboard.svelte';
    import PerClassMetricSection from '../PerClassMetricSection/PerClassMetricSection.svelte';
    import {
        compareRuns,
        leaderboardColumns,
        primaryMetric,
        sortByPrimaryMetric,
        type ComparableTaskType,
        type ComparedRun
    } from '../EvaluationComparison.helpers';

    interface Props {
        taskType: ComparableTaskType;
        runs: ComparedRun[];
    }

    const { taskType, runs }: Props = $props();

    const report = $derived(compareRuns(runs));
    const rankedRuns = $derived(sortByPrimaryMetric(runs, primaryMetric(taskType, runs)));
</script>

<div class="flex flex-col gap-6">
    <ComparabilityWarning {report} />
    <section class="flex flex-col gap-3">
        <h2 class="text-base font-semibold">Leaderboard</h2>
        <EvaluationLeaderboard
            runs={rankedRuns}
            columns={leaderboardColumns(taskType)}
            staleRunIds={report.staleRunIds}
        />
    </section>
    <PerClassMetricSection {taskType} runs={rankedRuns} />
</div>
