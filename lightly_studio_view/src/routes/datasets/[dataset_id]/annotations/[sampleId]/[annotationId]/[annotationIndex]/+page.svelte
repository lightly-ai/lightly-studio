<script lang="ts">
    import AnnotationDetails from '$lib/components/AnnotationDetails/AnnotationDetails.svelte';
    import { useImage } from '$lib/hooks/useImage/useImage.js';
    import { page } from '$app/state';
    import type { PageData } from './$types.js';

    const { data }: { data: PageData } = $props();
    const { annotationId, dataset, annotationIndex } = $derived(data);

    const sampleId = $derived(page.params.sampleId);

    const { image } = $derived(useImage({ sampleId }));
</script>

<div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="annotation-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">
        {#if $image.data && annotationId && dataset}
            <AnnotationDetails {annotationId} {annotationIndex} {dataset} image={$image.data} />
        {/if}
    </div>
</div>
