<script lang="ts">
    import { SampleType } from '$lib/api/lightly_studio_local/types.gen.js';
    import ImageAnnotationDetails from '$lib/components/AnnotationDetails/ImageAnnotationDetails/ImageAnnotationDetails.svelte';
    import VideoFrameAnnotationDetails from '$lib/components/AnnotationDetails/VideoFrameAnnotationDetails/VideoFrameAnnotationDetails.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation.js';
    import type { PageData } from './$types.js';
    import { page } from '$app/state';

    const { data }: { data: PageData } = $props();
    const { annotationId, dataset, annotationIndex } = $derived(data);

    const datasetId = page.params.dataset_id;

    const {
        annotation: annotationDetailsResponse,
        updateAnnotation,
        refetch
    } = $derived(
        useAnnotation({
            datasetId,
            annotationId
        })
    );
</script>

<div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="annotation-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">
        {#if $annotationDetailsResponse.data && annotationId && dataset}
            {#if $annotationDetailsResponse.data.parent_sample_type == SampleType.VIDEO}
                <VideoFrameAnnotationDetails
                    annotationDetails={$annotationDetailsResponse.data}
                    {annotationIndex}
                    {updateAnnotation}
                    {refetch}
                    {dataset}
                />
            {:else if $annotationDetailsResponse.data.parent_sample_type == SampleType.IMAGE}
                <ImageAnnotationDetails
                    annotationDetails={$annotationDetailsResponse.data}
                    {annotationIndex}
                    {updateAnnotation}
                    {refetch}
                    {dataset}
                />
            {/if}
        {/if}
    </div>
</div>
