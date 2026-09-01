<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { useAdjacentAnnotations } from '$lib/hooks/useAdjacentAnnotations/useAdjacentAnnotations';
    import { useAnnotationSortBy, useEvaluationRuns } from '$lib/hooks';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { TriangleAlert } from '@lucide/svelte';

    const STALE_WARNING =
        'Annotations changed after this evaluation ran, so the order you are stepping through is ' +
        'out of date. Go back to the grid view to recompute the evaluation.';

    interface Props {
        // The URL's dataset_id segment is a root collection ID, so it cannot query evaluation runs.
        collectionDatasetId: string;
    }

    const { collectionDatasetId }: Props = $props();

    const collectionId = $derived(page.params.collection_id!);
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);
    const annotationId = $derived(page.params.annotationId!);

    const { query: sampleAdjacentQuery } = $derived(
        useAdjacentAnnotations({
            sampleId: annotationId,
            collectionId
        })
    );

    const { sortByFor } = useAnnotationSortBy();
    const runsQuery = useEvaluationRuns(() => ({ datasetId: collectionDatasetId }));
    // Only the run the prev/next sequence is ordered by matters: any other stale run leaves it
    // intact.
    const activeRunId = $derived($sortByFor(collectionId)?.evaluation_run_id ?? null);
    const isActiveRunStale = $derived(
        (runsQuery.data ?? []).some((run) => run.id === activeRunId && run.stale_since !== null)
    );

    const gotoNextAnnotation = () => {
        if (sampleAdjacentQuery.data?.next_sample_id) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId,
                    collectionType,
                    collectionId,
                    annotationId: sampleAdjacentQuery.data?.next_sample_id
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const gotoPreviousAnnotation = () => {
        if (sampleAdjacentQuery.data?.previous_sample_id) {
            goto(
                routeHelpers.toSampleWithAnnotation({
                    datasetId,
                    collectionType,
                    collectionId,
                    annotationId: sampleAdjacentQuery.data?.previous_sample_id
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };
</script>

{#if sampleAdjacentQuery.data}
    <div data-testid="annotation-navigation">
        <SteppingNavigation
            hasPrevious={!!sampleAdjacentQuery.data?.previous_sample_id}
            hasNext={!!sampleAdjacentQuery.data?.next_sample_id}
            onPrevious={gotoPreviousAnnotation}
            onNext={gotoNextAnnotation}
        />
    </div>
{/if}

{#if isActiveRunStale}
    <!-- Overlays the image just above SteppingNavigation's next arrow, in its containing block. -->
    <Tooltip
        content={STALE_WARNING}
        ariaLabel={STALE_WARNING}
        position="bottom"
        triggerClass="absolute right-4 top-1/2 z-30 flex translate-y-[calc(-100%_-_1.5rem)] text-amber-400"
    >
        <span class="flex size-10 items-center justify-center rounded-full bg-black/60">
            <TriangleAlert class="size-6" data-testid="annotation-navigation-stale-icon" />
        </span>
    </Tooltip>
{/if}
