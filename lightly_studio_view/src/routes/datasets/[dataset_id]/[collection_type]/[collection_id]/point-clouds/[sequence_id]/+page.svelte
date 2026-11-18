<script lang="ts">
    import type { PageData } from './$types';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { useMcapSequenceSummary } from '$lib/hooks';
    import PointCloudLabelingWorkspace from '$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte';
    import { getTickNumberFromHash } from './getTickNumberFromHash';
    import { routeHelpers } from '$lib/routes';
    import { useAdjacentMcapSequences } from '$lib/hooks/useAdjacentMcapSequences/useAdjacentMcapSequences';

    const { data }: { data: PageData } = $props();
    const {
        datasetId,
        annotationSourceCollectionId,
        collectionId,
        collectionName,
        collectionType,
        sequenceId
    } = $derived(data);
    const tickNumber = $derived(getTickNumberFromHash(page.url.hash));
    // The workspace loads the same summary, so this query is deduplicated by TanStack.
    const { summary } = useMcapSequenceSummary({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId
    });
    const sourcePath = $derived([
        {
            label: 'Home',
            // The dataset_id URL slot is the root collection id, so the home crumb points the
            // collection id back at it. Using the dataset entity id here links to a collection
            // that does not exist and the collection layout load throws.
            href: routeHelpers.toCollectionHome(
                page.params.dataset_id!,
                collectionType,
                page.params.dataset_id!
            )
        },
        {
            label: collectionName,
            href: routeHelpers.toCollectionHome(
                page.params.dataset_id!,
                collectionType,
                collectionId
            )
        },
        {
            label: 'Point clouds',
            href: routeHelpers.toPointClouds(page.params.dataset_id!, collectionType, collectionId)
        },
        { label: summary.data?.file_name ?? `Point cloud ${sequenceId}` }
    ]);

    // Neighbours in the sequences grid order of the SEQUENCE collection.
    const { query: adjacentSequencesQuery } = $derived(
        useAdjacentMcapSequences({ sampleId: sequenceId, collectionId })
    );
    const previousSequenceId = $derived(adjacentSequencesQuery.data?.previous_sample_id);
    const nextSequenceId = $derived(adjacentSequencesQuery.data?.next_sample_id);

    // Opens on the first tick: the tick hash of the current sequence is not carried over.
    const goToSequence = (targetSequenceId: string) => {
        void goto(
            routeHelpers.toPointCloudLabeling({
                datasetId: page.params.dataset_id!,
                collectionType,
                collectionId,
                sequenceId: targetSequenceId
            })
        );
    };

    const updateTickNumber = (nextTickNumber: number) => {
        const url = new URL(page.url);
        const hash = new URLSearchParams(url.hash.slice(1));
        hash.set('tick', String(nextTickNumber));
        url.hash = hash.toString();
        void goto(url, {
            replaceState: true,
            noScroll: true,
            keepFocus: true,
            state: page.state
        });
    };
</script>

<div
    class="flex h-full min-h-0 w-full flex-1 bg-card px-2 pb-2 pt-4"
    data-testid="point-cloud-labeling-route"
>
    <div class="h-full min-h-0 w-full overflow-hidden">
        <PointCloudLabelingWorkspace
            {datasetId}
            {collectionId}
            {annotationSourceCollectionId}
            {sequenceId}
            {sourcePath}
            {tickNumber}
            onTickChange={updateTickNumber}
            onPreviousSequence={previousSequenceId
                ? () => goToSequence(previousSequenceId)
                : undefined}
            onNextSequence={nextSequenceId ? () => goToSequence(nextSequenceId) : undefined}
        />
    </div>
</div>
