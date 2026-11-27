<script lang="ts">
    import type { PageData } from './$types';
    import { page } from '$app/state';
    import { useMcapSequenceSummary } from '$lib/hooks';
    import PointCloudLabelingWorkspace from '$lib/components/PointCloudLabelingWorkspace/PointCloudLabelingWorkspace.svelte';
    import type { WorkspaceCrumb } from '$lib/components/PointCloudLabelingWorkspace/types';
    import { useCanNavigateDataset } from '$lib/hooks/useCanNavigateDataset/useCanNavigateDataset';
    import { useSequenceHashState } from './useSequenceHashState.svelte';
    import { routeHelpers } from '$lib/routes';
    import { useSequenceNeighbours } from './useSequenceNeighbours.svelte';
    import {
        createWorkflowFileContext,
        getWorkflowParams
    } from '$lib/contexts/WorkflowFile.svelte';

    const { data }: { data: PageData } = $props();
    const {
        datasetId,
        annotationSourceCollectionId,
        collectionId,
        collectionName,
        collectionType,
        sequenceId
    } = $derived(data);
    // A sequence opened from a hosted workflow batch is that batch's file: the header shows
    // its state and transitions, and editing follows whose turn it is.
    const workflow = createWorkflowFileContext(() => getWorkflowParams(page.url, sequenceId));
    const hashState = useSequenceHashState({ getSequenceId: () => sequenceId });
    // The workspace loads the same summary, so this query is deduplicated by TanStack.
    const { summary } = useMcapSequenceSummary({
        getDatasetId: () => datasetId,
        getSequenceId: () => sequenceId
    });
    const fileLabel = $derived(summary.data?.file_name ?? `Point cloud ${sequenceId}`);
    const projectsHome: WorkspaceCrumb = {
        label: 'Home',
        href: routeHelpers.toWorkspaceProjects(),
        reload: true
    };
    // In a batch the crumbs lead back to the batch in the hosted workspace app (a full page
    // load), never into the dataset.
    const batchPath = $derived.by((): WorkspaceCrumb[] => {
        // Without the batch file only Projects is safe to link to: show Home and the file name
        // once loading failed, and nothing while it loads.
        if (workflow.isError) return [projectsHome, { label: fileLabel }];
        const file = workflow.file;
        if (!file) return [];
        const projectHref = `/workspace/projects/${file.project_id}`;
        return [
            projectsHome,
            { label: file.project_name, href: projectHref, reload: true },
            {
                label: file.batch_name,
                href: `${projectHref}/batches/${file.batch_id}`,
                reload: true
            },
            { label: fileLabel }
        ];
    });
    // Labelers keep their bearings outside a batch but cannot leave for the dataset from here;
    // their Home crumb goes back to Projects instead.
    const canNavigate = useCanNavigateDataset();
    const datasetLinks = $derived([
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
        { label: fileLabel }
    ]);
    const datasetPath = $derived(
        canNavigate
            ? datasetLinks
            : [projectsHome, ...datasetLinks.slice(1).map(({ label }) => ({ label }))]
    );
    const neighbours = useSequenceNeighbours({
        getSequenceId: () => sequenceId,
        getCollectionId: () => collectionId,
        getCollectionType: () => collectionType,
        workflow
    });
    // Opened from the dataset grid, the crumbs lead back to the dataset, also in workflow mode.
    const sourcePath = $derived(neighbours.batchOrder ? batchPath : datasetPath);

    // A finished Submit / Accept / Rework opens the same sequence as the next-sequence button.
    $effect(() => {
        const onNextSequence = neighbours.onNextSequence;
        if (onNextSequence) return workflow.registerNext(onNextSequence);
    });
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
            tickNumber={hashState.tick}
            openCamera={hashState.openCamera}
            onOpenCameraChange={hashState.setOpenCamera}
            onTickChange={hashState.setTick}
            onPreviousSequence={neighbours.onPreviousSequence}
            onNextSequence={neighbours.onNextSequence}
        />
    </div>
</div>
