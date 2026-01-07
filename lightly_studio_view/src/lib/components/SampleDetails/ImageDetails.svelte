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

    // Setup keyboard shortcuts
    // Handle Escape key
    const handleEscape = () => {
        goto(routeHelpers.toSamples(collectionId));
    };

    const { image, refetch } = $derived(useImage({ sampleId }));

    let sampleURL = $derived(getImageURL(sampleId));
</script>

<SampleDetailsPanel
    {collectionId}
    {sampleId}
    {sampleURL}
    sample={$image.data?.sample
        ? {
              ...$image.data?.sample,
              width: $image.data.width,
              height: $image.data.height,
              annotations: $image.data?.annotations
          }
        : undefined}
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
        <SampleMetadata sample={$image.data} />
    {/snippet}
</SampleDetailsPanel>
