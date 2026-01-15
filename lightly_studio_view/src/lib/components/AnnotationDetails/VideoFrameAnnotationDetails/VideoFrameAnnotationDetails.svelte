<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type {
        AnnotationDetailsWithPayloadView,
        AnnotationUpdateInput,
        VideoFrameAnnotationDetailsView
    } from '$lib/api/lightly_studio_local';
    import FrameDetailsSegment from '$lib/components/frames/FrameDetailsSegment/FrameDetailsSegment.svelte';
    import { routeHelpers } from '$lib/routes';
    import type { Collection } from '$lib/services/types';
    import AnnotationDetails from '../AnnotationDetails.svelte';
    import AnnotationViewSampleContainer from '../AnnotationViewSampleContainer/AnnotationViewSampleContainer.svelte';
    import { page } from '$app/state';

    const {
        annotationIndex,
        collection,
        annotationDetails,
        updateAnnotation,
        refetch
    }: {
        collection: Collection;
        annotationDetails: AnnotationDetailsWithPayloadView;
        annotationIndex?: number;
        updateAnnotation: (input: AnnotationUpdateInput) => Promise<void>;
        refetch: () => void;
    } = $props();

    const videoFrame = $derived(
        annotationDetails.parent_sample_data as VideoFrameAnnotationDetailsView
    );
    // Get route parameters from page
    const datasetId = $derived(page.params.dataset_id ?? page.data?.datasetId);
    const frameCollectionId = $derived(videoFrame?.sample?.collection_id);
    const frameCollectionType = $derived('video_frame');
</script>

{#if videoFrame?.video && (videoFrame.sample_id || videoFrame?.sample?.sample_id)}
    <AnnotationDetails
        {annotationDetails}
        {updateAnnotation}
        {refetch}
        {annotationIndex}
        collectionId={collection.collection_id!}
        parentSample={{
            width: videoFrame.video.width,
            height: videoFrame.video.height,
            url: `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${videoFrame.sample_id || videoFrame.sample?.sample_id}`
        }}
    >
        {#snippet parentSampleDetails()}
            <AnnotationViewSampleContainer
                href={datasetId && frameCollectionId
                    ? routeHelpers.toFramesDetails(
                          datasetId,
                          frameCollectionType,
                          frameCollectionId,
                          videoFrame.sample_id || videoFrame.sample?.sample_id || ''
                      )
                    : '#'}
            >
                <FrameDetailsSegment sample={videoFrame} />
            </AnnotationViewSampleContainer>
        {/snippet}
    </AnnotationDetails>
{:else}
    <div class="flex h-full w-full items-center justify-center">
        <p>Loading video frame data...</p>
    </div>
{/if}
