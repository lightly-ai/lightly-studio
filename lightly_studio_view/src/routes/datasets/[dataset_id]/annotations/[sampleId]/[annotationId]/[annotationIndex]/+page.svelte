<script lang="ts">
    import AnnotationDetails from '$lib/components/AnnotationDetails/AnnotationDetails.svelte';
    import type { PageData } from './$types.js';

    const { data }: { data: PageData } = $props();
    const { annotationId, dataset, annotationIndex } = $derived(data);
</script>

<div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="annotation-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">
        {#if annotationId && dataset}
            <AnnotationDetails {annotationId} {annotationIndex} {dataset} />
        {/if}
    </div>
</div>
