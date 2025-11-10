<script lang="ts">
    import AnnotationDetails from '$lib/components/AnnotationDetails/AnnotationDetails.svelte';
    import { useSample } from '$lib/hooks/useSample/useSample.js';
    import { page } from '$app/state';
    import type { PageData } from './$types.js';

    const { data }: { data: PageData } = $props();
    const { annotationId, dataset, annotationIndex } = $derived(data);

    const sampleId = $derived(page.params.sampleId);

    const { sample } = $derived(useSample({ sampleId }));
</script>

<div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="annotation-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">
        {#if $sample.data && annotationId && dataset}
            <AnnotationDetails {annotationId} {annotationIndex} {dataset} sample={$sample.data} />
        {/if}
    </div>
</div>
