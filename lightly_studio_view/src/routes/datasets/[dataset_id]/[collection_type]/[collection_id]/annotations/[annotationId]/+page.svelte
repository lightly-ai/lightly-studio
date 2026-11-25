<script lang="ts">
    import { SampleType } from '$lib/api/lightly_studio_local/types.gen.js';
    import ImageAnnotationDetails from '$lib/components/AnnotationDetails/ImageAnnotationDetails/ImageAnnotationDetails.svelte';
    import VideoFrameAnnotationDetails from '$lib/components/AnnotationDetails/VideoFrameAnnotationDetails/VideoFrameAnnotationDetails.svelte';
    import type { PageData } from './$types.js';
    import { useAnnotationDetails } from '$lib/hooks/useAnnotationDetails/useAnnotationsDetails.js';

    import { page } from '$app/state';

    const { data }: { data: PageData } = $props();
    const { collection } = $derived(data);

    const collectionId = $derived(page.params.collection_id!);

    const annotationId = $derived(page.params.annotationId!);

    const {
        annotation: annotationDetailsResponse,
        updateAnnotation,
        refetch
    } = $derived(
        useAnnotationDetails({
            collectionId,
            annotationId
        })
    );
</script>

<div class="flex h-full w-full bg-card px-2 pb-2 pt-4" data-testid="annotation-details">
    <div class="h-full w-full">
        {#if annotationDetailsResponse.data && annotationId && collection}
            {#if annotationDetailsResponse.data.parent_sample_type == SampleType.VIDEO_FRAME}
                <VideoFrameAnnotationDetails
                    annotationDetails={annotationDetailsResponse.data}
                    {updateAnnotation}
                    {refetch}
                    {collection}
                />
            {:else if annotationDetailsResponse.data.parent_sample_type == SampleType.IMAGE}
                <ImageAnnotationDetails
                    annotationDetails={annotationDetailsResponse.data}
                    {updateAnnotation}
                    {refetch}
                    {collection}
                />
            {/if}
        {/if}
    </div>
</div>
