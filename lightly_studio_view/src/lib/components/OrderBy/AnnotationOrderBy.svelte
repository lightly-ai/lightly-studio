<script lang="ts">
    import {
        useAnnotationOrderBy,
        useAnnotationSortBy,
        useEvaluationRuns,
        useGlobalStorage,
        useHasEmbeddings,
        usePostHog,
        useRecomputeEvaluationRun
    } from '$lib/hooks';
    import { type SelectItem } from '$lib/components/Select';
    import { Button } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { RefreshCw, TriangleAlert } from '@lucide/svelte';
    import OrderByControl from './OrderByControl.svelte';

    const STALE_WARNING =
        'Annotations changed after this evaluation ran, so this sort order is out of date. ' +
        'Recompute the evaluation to refresh it.';

    interface Props {
        /** The browsed annotation source. */
        collectionId: string;
        /** The dataset the annotation source belongs to. Owns the evaluation runs. */
        datasetId: string;
    }

    const { collectionId, datasetId }: Props = $props();

    const { textEmbedding } = useGlobalStorage();
    const { trackEvent } = usePostHog();
    const hasEmbeddingsQuery = useHasEmbeddings(() => ({ collectionId }));
    // Similarity ordering keeps precedence over metric sorting, so the control is disabled while
    // a search applies to this source. A search started elsewhere persists but cannot be applied
    // to a source without embeddings, and the grid keeps sorting there. The selection survives
    // clearing the search.
    const isSimilaritySearchActive = $derived(!!$textEmbedding && !!hasEmbeddingsQuery.data);

    const {
        allSortFields,
        selectedDirection,
        selectedIndex,
        handleFieldClick,
        toggleDirection,
        dispose
    } = useAnnotationOrderBy({ collectionId: () => collectionId });

    $effect(() => {
        return () => dispose();
    });

    const { sortByFor } = useAnnotationSortBy();
    const runsQuery = useEvaluationRuns(() => ({ datasetId }));
    // Only the run the grid is sorted by matters: any other stale run leaves this order intact.
    const activeRunId = $derived($sortByFor(collectionId)?.evaluation_run_id ?? null);
    const isActiveRunStale = $derived(
        (runsQuery.data ?? []).some((run) => run.id === activeRunId && run.stale_since !== null)
    );

    const { mutation, recompute } = useRecomputeEvaluationRun(() => ({
        datasetId,
        runId: activeRunId ?? ''
    }));
    const recomputeLabel = $derived(mutation.isPending ? 'Recomputing…' : 'Recompute evaluation');

    const selectValue = $derived($selectedIndex >= 0 ? String($selectedIndex) : '');

    const sortItems = $derived<SelectItem[]>(
        $allSortFields.map((field, i) => ({
            value: String(i),
            label: field.label,
            testId: `sort-field-${field.evaluation_run_id}-${field.metric_name}`
        }))
    );

    const handleValueChange = (value: string) => {
        if (value === '') {
            if ($selectedIndex >= 0) handleFieldClick($allSortFields[$selectedIndex]);
            return;
        }
        const field = $allSortFields[Number(value)];
        if (field) handleFieldClick(field);
    };
</script>

<div class="flex items-center gap-1">
    <OrderByControl
        items={sortItems}
        selectedValue={selectValue}
        triggerLabel={$allSortFields[$selectedIndex]?.label}
        direction={$selectedDirection}
        disabled={isSimilaritySearchActive}
        allowDeselect
        onValueChange={handleValueChange}
        onOpen={() => trackEvent('sort_by_opened', { collection_id: collectionId })}
        onToggleDirection={toggleDirection}
    />

    {#if isActiveRunStale}
        <Tooltip
            content={STALE_WARNING}
            ariaLabel={STALE_WARNING}
            position="bottom"
            triggerClass="inline-flex"
        >
            <TriangleAlert
                class="size-3.5 shrink-0 text-amber-500 dark:text-amber-400"
                data-testid="annotation-sort-stale-icon"
            />
        </Tooltip>

        <Tooltip content={recomputeLabel} position="bottom">
            <Button
                variant="ghost"
                icon={RefreshCw}
                ariaLabel={recomputeLabel}
                isPending={mutation.isPending}
                buttonProps={{
                    type: 'button',
                    size: 'icon',
                    disabled: mutation.isPending,
                    onclick: recompute,
                    class: 'size-auto p-0 hover:bg-transparent',
                    'data-testid': 'annotation-sort-recompute-button'
                }}
            />
        </Tooltip>
    {/if}
</div>
