<script lang="ts">
    import { ApiError } from '$lib/api/ApiError';
    import { Spinner } from '$lib/components';
    import { useEvaluationRuns, useEvaluationRunsMetrics, useTags } from '$lib/hooks';
    import EvaluationComparisonView from './EvaluationComparisonView/EvaluationComparisonView.svelte';
    import {
        SELECTION_PROBLEM_MESSAGES,
        isComparableTaskType,
        validateSelection,
        type ComparedRun
    } from './EvaluationComparison.helpers';

    interface Props {
        datasetId: string;
        /** Collection of the page. The tag picker shows its tags. */
        collectionId: string;
        /** Runs from the page link, in link order. */
        runIds: string[];
        /** Tags from the page link to compare the runs on. */
        tagIds: string[];
        onTagIdsChange: (tagIds: string[]) => void;
        /** Link back to the images of the collection. */
        imagesHref: string;
    }

    const { datasetId, collectionId, runIds, tagIds, onTagIdsChange, imagesHref }: Props = $props();

    const { tags } = $derived(useTags({ collection_id: collectionId }));
    // A shared link can name tags that were deleted later. Compare only the tags that exist.
    const existingTagIds = $derived(
        tagIds.filter((tagId) => $tags.some((tag) => tag.tag_id === tagId))
    );

    const HTTP_STATUS_NOT_FOUND = 404;

    const runsQuery = useEvaluationRuns(() => ({ datasetId }));
    const runsById = $derived(new Map((runsQuery.data ?? []).map((run) => [run.id, run])));
    const selectedRuns = $derived(runIds.flatMap((id) => runsById.get(id) ?? []));
    const hasUnknownRun = $derived(
        runsQuery.data !== undefined && selectedRuns.length < runIds.length
    );
    const selectionProblem = $derived(validateSelection(selectedRuns));
    const canCompare = $derived(
        runsQuery.data !== undefined && !hasUnknownRun && selectionProblem === null
    );

    const metricsQuery = useEvaluationRunsMetrics(() => ({
        datasetId,
        runIds,
        tagIds: existingTagIds,
        enabled: canCompare
    }));
    const isMetricsNotFound = $derived(
        metricsQuery.error instanceof ApiError &&
            metricsQuery.error.status === HTTP_STATUS_NOT_FOUND
    );
    const comparedRuns: ComparedRun[] = $derived(
        (metricsQuery.data ?? []).flatMap((metrics) => {
            const run = runsById.get(metrics.evaluation_run_id);
            return run ? [{ run, metrics }] : [];
        })
    );
    const taskType = $derived(selectedRuns[0]?.task_type);
</script>

<div class="flex flex-col gap-4 p-6" data-testid="evaluation-comparison">
    <div class="flex items-center justify-between">
        <h1 class="text-xl font-semibold">Compare evaluation runs</h1>
        <a class="text-sm underline" href={imagesHref}>Back to images</a>
    </div>
    {#if hasUnknownRun || isMetricsNotFound}
        <p>Evaluation run not found.</p>
    {:else if runsQuery.error}
        <p class="text-destructive-text">{runsQuery.error.message}</p>
    {:else if runsQuery.data === undefined || metricsQuery.isLoading}
        <Spinner />
    {:else if selectionProblem !== null}
        <p>{SELECTION_PROBLEM_MESSAGES[selectionProblem]}</p>
    {:else if metricsQuery.error}
        <p class="text-destructive-text">{metricsQuery.error.message}</p>
    {:else if taskType && isComparableTaskType(taskType)}
        <EvaluationComparisonView
            {taskType}
            runs={comparedRuns}
            tags={$tags}
            selectedTagIds={existingTagIds}
            onSelectedTagIdsChange={onTagIdsChange}
        />
    {/if}
</div>
