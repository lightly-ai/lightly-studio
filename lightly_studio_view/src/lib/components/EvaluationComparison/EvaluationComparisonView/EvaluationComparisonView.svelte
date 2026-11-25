<script lang="ts">
    import ComparabilityWarning from '../ComparabilityWarning/ComparabilityWarning.svelte';
    import EvaluationLeaderboard from '../EvaluationLeaderboard/EvaluationLeaderboard.svelte';
    import PerClassMetricSection from '../PerClassMetricSection/PerClassMetricSection.svelte';
    import TagSection from '../TagSection/TagSection.svelte';
    import type { TagView } from '$lib/api/lightly_studio_local';
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
        tags: Pick<TagView, 'tag_id' | 'name'>[];
        selectedTagIds: string[];
        onSelectedTagIdsChange: (tagIds: string[]) => void;
    }

    const { taskType, runs, tags, selectedTagIds, onSelectedTagIdsChange }: Props = $props();

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
    <TagSection {taskType} runs={rankedRuns} {tags} {selectedTagIds} {onSelectedTagIdsChange} />
    <PerClassMetricSection {taskType} runs={rankedRuns} />
</div>
