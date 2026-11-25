<script lang="ts">
    import type { TagView } from '$lib/api/lightly_studio_local';
    import * as Tabs from '$lib/components/ui/tabs';
    import {
        LEADERBOARD_METRIC_LABELS,
        leaderboardColumns,
        primaryMetric,
        tagRows,
        type ComparableTaskType,
        type ComparedRun,
        type LeaderboardMetric
    } from '../EvaluationComparison.helpers';
    import TagMetricTable from './TagMetricTable/TagMetricTable.svelte';
    import TagPicker from './TagPicker/TagPicker.svelte';

    interface Props {
        taskType: ComparableTaskType;
        /** Runs in display order, with one slice for each selected tag. */
        runs: ComparedRun[];
        tags: Pick<TagView, 'tag_id' | 'name'>[];
        selectedTagIds: string[];
        onSelectedTagIdsChange: (tagIds: string[]) => void;
    }

    const { taskType, runs, tags, selectedTagIds, onSelectedTagIdsChange }: Props = $props();

    const metrics = $derived(leaderboardColumns(taskType));
    let selectedMetric = $state<string>('');
    const activeMetric: LeaderboardMetric = $derived(
        metrics.find((metric) => metric === selectedMetric) ?? primaryMetric(taskType, runs)
    );
    const rows = $derived(tagRows(runs, activeMetric));
</script>

<section class="flex flex-col gap-3" data-testid="tag-section">
    <div class="flex items-center justify-between">
        <h2 class="text-base font-semibold">Tags</h2>
        {#if selectedTagIds.length > 0}
            <Tabs.Root value={activeMetric} onValueChange={(value) => (selectedMetric = value)}>
                <Tabs.List>
                    {#each metrics as metric (metric)}
                        <Tabs.Trigger value={metric}
                            >{LEADERBOARD_METRIC_LABELS[metric]}</Tabs.Trigger
                        >
                    {/each}
                </Tabs.List>
            </Tabs.Root>
        {/if}
    </div>
    <TagPicker {tags} {selectedTagIds} {onSelectedTagIdsChange} />
    {#if selectedTagIds.length === 0}
        <p class="text-sm text-muted-foreground">
            Select tags to compare the runs on subsets of the images.
        </p>
    {:else}
        <TagMetricTable runNames={runs.map((entry) => entry.run.name)} {rows} />
    {/if}
</section>
