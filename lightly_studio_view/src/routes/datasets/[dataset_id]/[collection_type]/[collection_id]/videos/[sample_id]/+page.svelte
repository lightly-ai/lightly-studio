<script lang="ts">
    import { page } from '$app/state';
    import { VideoDetails } from '$lib/components';
    import VideoDetailsBreadcrumb from '$lib/components/VideoDetailsBreadcrumb/VideoDetailsBreadcrumb.svelte';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import type { PageData } from './$types';

    const { data }: { data: PageData } = $props();
    const { sample }: { sample: PageData['sample'] } = $derived(data);

    // Route validations in +layout.ts ensure these params are always present and valid
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    const { collection: datasetCollection } = $derived.by(() =>
        useCollectionWithChildren({
            collectionId: datasetId
        })
    );
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex w-full items-center">
        {#if $datasetCollection.data && !Array.isArray($datasetCollection.data)}
            <VideoDetailsBreadcrumb
                rootCollection={$datasetCollection.data}
                {datasetId}
                {collectionType}
                sampleId={page.params.sample_id}
            />
        {/if}
    </div>
    <Separator class="mb-4 bg-border-hard" />
    {#if sample}
        <VideoDetails video={sample} />
    {/if}
</div>
