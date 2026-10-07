<script lang="ts">
    import type { PageData } from './$types';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { useFeatureFlags, useMcapSequenceSummary } from '$lib/hooks';
    import { LayoutCard } from '$lib/components';
    import PointCloudLabelingWorkspace from '$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte';
    import { getTickNumberFromHash } from './getTickNumberFromHash';
    import { routeHelpers } from '$lib/routes';

    // The backend only reports this once LIGHTLY_STUDIO_POINT_CLOUD_ENABLED is set, so
    // this one string keeps the route (and the entry point in GroupsComponentsMenu) in sync with
    // lightly_studio/api/features.py. Disabling it never affects the existing sample detail view.
    const POINT_CLOUD_RENDERING_FEATURE = 'point_cloud_rendering';
    const { data }: { data: PageData } = $props();
    const {
        datasetId,
        annotationSourceCollectionId,
        collectionId,
        collectionName,
        collectionType,
        sequenceId
    } = $derived(data);
    const { featureFlags } = useFeatureFlags();
    const isEnabled = $derived($featureFlags.includes(POINT_CLOUD_RENDERING_FEATURE));
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

<div class="flex h-full min-h-0 w-full flex-1 px-4 pb-4" data-testid="point-cloud-labeling-route">
    {#if isEnabled}
        <LayoutCard className="min-h-0 overflow-hidden px-4 py-2">
            <PointCloudLabelingWorkspace
                {datasetId}
                {annotationSourceCollectionId}
                {sequenceId}
                {sourcePath}
                {tickNumber}
                onTickChange={updateTickNumber}
            />
        </LayoutCard>
    {/if}
</div>
