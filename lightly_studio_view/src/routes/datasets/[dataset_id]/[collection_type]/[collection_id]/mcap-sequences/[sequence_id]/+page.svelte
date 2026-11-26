<script lang="ts">
    import type { PageData } from './$types';
    import { afterNavigate, goto } from '$app/navigation';
    import { page } from '$app/state';
    import { useMcapSequenceSummary } from '$lib/hooks';
    import { LayoutCard } from '$lib/components';
    import PointCloudLabelingWorkspace from '$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte';
    import { buildSequenceHash, getCameraFromHash, getTickNumberFromHash } from './sequenceHash';
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
    // Playback writes the hash every tick, so the route owns the tick and camera and always
    // builds the whole hash from both instead of patching a `page.url` that may be stale.
    let currentTick = $state(getTickNumberFromHash(page.url.hash));
    let openCamera = $state(getCameraFromHash(page.url.hash));
    // True while this page session pushed the history entry of the open camera.
    let pushedCameraEntry = $state(false);
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
            href: routeHelpers.toMcapSequences(
                page.params.dataset_id!,
                collectionType,
                collectionId
            )
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

    const syncFromUrl = () => {
        currentTick = getTickNumberFromHash(page.url.hash);
        openCamera = getCameraFromHash(page.url.hash);
        pushedCameraEntry = false;
    };

    // Another sequence starts without a hash, so drop the tick and camera of the previous one.
    let syncedSequenceId: string | undefined;
    $effect.pre(() => {
        const previousSequenceId = syncedSequenceId;
        syncedSequenceId = sequenceId;
        if (previousSequenceId !== undefined && previousSequenceId !== sequenceId) syncFromUrl();
    });

    afterNavigate(({ type }) => {
        if (type === 'popstate') syncFromUrl();
    });

    const writeHash = (historyMode: 'push' | 'replace') => {
        const url = new URL(page.url);
        url.hash = buildSequenceHash({ tick: currentTick, camera: openCamera });
        void goto(url, {
            replaceState: historyMode === 'replace',
            noScroll: true,
            keepFocus: true,
            state: page.state
        });
    };

    const updateTickNumber = (nextTickNumber: number) => {
        currentTick = nextTickNumber;
        writeHash('replace');
    };

    const setOpenCamera = (camera: string | undefined, historyMode: 'push' | 'replace') => {
        if (camera === undefined && pushedCameraEntry) {
            // Pop the entry that opened the camera, so back and close leave the same page.
            openCamera = undefined;
            pushedCameraEntry = false;
            history.back();
            return;
        }
        openCamera = camera;
        if (camera === undefined) pushedCameraEntry = false;
        else pushedCameraEntry ||= historyMode === 'push';
        writeHash(historyMode);
    };
</script>

<div class="flex h-full min-h-0 w-full flex-1 px-4 pb-4" data-testid="point-cloud-labeling-route">
    <LayoutCard className="min-h-0 overflow-hidden px-4 py-2">
        <PointCloudLabelingWorkspace
            {datasetId}
            {annotationSourceCollectionId}
            {sequenceId}
            {sourcePath}
            tickNumber={currentTick}
            {openCamera}
            onOpenCameraChange={setOpenCamera}
            onTickChange={updateTickNumber}
            onPreviousSequence={previousSequenceId
                ? () => goToSequence(previousSequenceId)
                : undefined}
            onNextSequence={nextSequenceId ? () => goToSequence(nextSequenceId) : undefined}
        />
    </LayoutCard>
</div>
