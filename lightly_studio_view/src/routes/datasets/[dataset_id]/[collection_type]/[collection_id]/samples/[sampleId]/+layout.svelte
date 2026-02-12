<script lang="ts">
    import { page } from '$app/state';
    import { createSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { ImageDetails } from '$lib/components';

    const { children } = $props();

    createSampleDetailsToolbarContext();

    const sampleId = $derived(page.params.sampleId);
    const collection = page.data.collection;
    const sampleIndex = $derived(Number(page.params.sampleIndex));
</script>

<div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="sample-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">
        <ImageDetails {sampleId} {collection} {sampleIndex}>
            {#if children}
                {@render children()}
            {/if}
        </ImageDetails>
    </div>
</div>
