<script lang="ts">
    import LayoutCard from '../LayoutCard/LayoutCard.svelte';
    import ImageDetails from '../SampleDetails/ImageDetails.svelte';

    import { page } from '$app/state';

    const sampleId = $derived(page.params.sampleId);
    const collection = page.data.collection;

    $inspect(sampleId, 'sampleId');
    $inspect(collection, 'collection');
</script>

<div class="flex flex-row gap-4 p-4">
    <div class="min-w-[250px] max-w-[30%]">
        <LayoutCard>Group adjacent sample</LayoutCard>
    </div>
    <div class="flex-1">
        <LayoutCard>Image details</LayoutCard>
    </div>
</div>

<!-- <div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="sample-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4"></div>
</div> -->
