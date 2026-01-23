<script lang="ts">
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import { type Snippet } from 'svelte';
    import { getImageURL } from '$lib/utils/getImageURL';
    import { useImage } from '$lib/hooks/useImage/useImage';
    import type { Collection } from '$lib/services/types';
    import SampleDetailsPanel from './SampleDetailsPanel.svelte';
    import SampleMetadata from '../SampleMetadata/SampleMetadata.svelte';
    import SampleDetailsBreadcrumb from './SampleDetailsBreadcrumb/SampleDetailsBreadcrumb.svelte';
    import { page } from '$app/state';
    import type { ImageView } from '$lib/api/lightly_studio_local';

    const {
        sampleId,
        collection,
        sampleIndex,
        children
    }: {
        sampleId: string;
        collection: Collection;
        sampleIndex?: number;
        children: Snippet | undefined;
    } = $props();

    const collectionId = collection.collection_id!;

    // Get route parameters from page
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    // Setup keyboard shortcuts
    // Handle Escape key
    const handleEscape = () => {
        if (datasetId && collectionType) {
            goto(routeHelpers.toSamples(datasetId, collectionType, collectionId));
        }
    };

    const { image, refetch } = $derived(useImage({ sampleId }));

    let sampleURL = $derived(getImageURL(sampleId));
    const sampleImage = $derived($image.data as ImageView | undefined);
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
        {/if}
        {#snippet breadcrumb({ collection: rootCollection })}
            <SampleDetailsBreadcrumb {rootCollection} {sampleIndex} />
        {/snippet}
        {#snippet metadataValue()}
            <SampleMetadata sample={sampleImage} />
        {/snippet}
    </SampleDetailsPanel>
{/if}
