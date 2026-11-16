<script lang="ts">
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import { type Snippet } from 'svelte';
    import { getImageURLById } from '$lib/utils';
    import { useImage } from '$lib/hooks/useImage/useImage';
    import type { Collection } from '$lib/services/types';
    import SampleDetailsPanel from './SampleDetailsPanel.svelte';
    import SampleMetadata from '../SampleMetadata/SampleMetadata.svelte';
    import SampleDetailsBreadcrumb from './SampleDetailsBreadcrumb/SampleDetailsBreadcrumb.svelte';
    import { page } from '$app/state';
    import type { ImageView } from '$lib/api/lightly_studio_local';
    import SampleDetailsNavigation from './SampleDetailsNavigation/SampleDetailsNavigation.svelte';
    import WorkflowBreadcrumb from '$lib/components/Workflow/WorkflowBreadcrumb/WorkflowBreadcrumb.svelte';
    import WorkflowNavigation from '$lib/components/Workflow/WorkflowNavigation/WorkflowNavigation.svelte';
    import {
        createWorkflowFileContext,
        getWorkflowParams
    } from '$lib/contexts/WorkflowFile.svelte';

    const {
        sampleId,
        collection,
        children
    }: {
        sampleId: string;
        collection: Collection;
        children?: Snippet;
    } = $props();

    const collectionId = $derived(collection.collection_id!);

    // Get route parameters from page
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    // Setup keyboard shortcuts
    // Handle Escape key
    const handleEscape = () => {
        if (datasetId && collectionType) {
            goto(routeHelpers.toImages(datasetId, collectionType, collectionId));
        }
    };

    const { image, refetch } = useImage(() => ({ sampleId }));

    // A sample opened from a hosted workflow batch shows the batch instead of the collection.
    const workflow = createWorkflowFileContext(() => getWorkflowParams(page.url, sampleId));

    let sampleURL = $derived(getImageURLById(sampleId));
    const sampleImage = $derived(image.data as ImageView | undefined);
</script>

{#if sampleImage}
    <SampleDetailsPanel
        {collectionId}
        {sampleId}
        {sampleURL}
        sample={{
            ...sampleImage.sample,
            width: sampleImage.width,
            height: sampleImage.height,
            annotations: sampleImage.annotations
        }}
        {refetch}
        {handleEscape}
    >
        {#if children}
            {@render children()}
            {#if !workflow.active}
                <SampleDetailsNavigation />
            {:else if workflow.file}
                <WorkflowNavigation
                    previousSampleId={workflow.file.previous_sample_id}
                    nextSampleId={workflow.file.next_sample_id}
                />
            {/if}
        {/if}
        {#snippet breadcrumb({ collection: rootCollection })}
            {#if !workflow.active}
                <SampleDetailsBreadcrumb {rootCollection} />
            {:else if workflow.file}
                <WorkflowBreadcrumb file={workflow.file} />
            {/if}
        {/snippet}
        {#snippet metadataValue()}
            <SampleMetadata sample={sampleImage} />
        {/snippet}
    </SampleDetailsPanel>
{/if}
