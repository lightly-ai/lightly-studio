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
</script>

<AnnotationDetails
    {annotationDetails}
    {updateAnnotation}
    {refetch}
    {annotationIndex}
    {collection}
    collectionId={collection.collection_id!}
    parentSample={{
        width: videoFrame.video.width,
        height: videoFrame.video.height,
        url: `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${videoFrame.sample_id}`
    }}
>
    {#snippet parentSampleDetails()}
        <AnnotationViewSampleContainer
            href={routeHelpers.toFramesDetails(
                videoFrame.sample.collection_id,
                videoFrame.sample_id
            )}
        >
            <FrameDetailsSegment sample={videoFrame} />
        </AnnotationViewSampleContainer>
    {/snippet}
</AnnotationDetails>
