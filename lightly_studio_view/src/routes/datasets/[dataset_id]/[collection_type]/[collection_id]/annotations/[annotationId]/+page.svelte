<script lang="ts">
    import { SampleType } from '$lib/api/lightly_studio_local/types.gen.js';
    import ImageAnnotationDetails from '$lib/components/AnnotationDetails/ImageAnnotationDetails/ImageAnnotationDetails.svelte';
    import VideoFrameAnnotationDetails from '$lib/components/AnnotationDetails/VideoFrameAnnotationDetails/VideoFrameAnnotationDetails.svelte';
    import type { PageData } from './$types.js';
    import { useAnnotationDetails } from '$lib/hooks/useAnnotationDetails/useAnnotationsDetails.js';

    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import { useOpenSample } from '$lib/hooks/useOpenSample/useOpenSample';

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

    // Reopen this annotation when the user comes back to the tab.
    const { rememberOpenSample, forgetOpenSample } = useOpenSample();
    $effect(() => {
        rememberOpenSample(collectionId, page.url.pathname + page.url.search);
    });
    // The remembered annotation can be deleted by then, so fall back to the grid.
    $effect(() => {
        if (!annotationDetailsResponse.isError) return;
        forgetOpenSample(collectionId);
        goto(
            routeHelpers.toAnnotations(
                page.params.dataset_id!,
                page.params.collection_type!,
                collectionId
            ),
            { replaceState: true }
        );
    });
</script>

<div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="annotation-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">
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
