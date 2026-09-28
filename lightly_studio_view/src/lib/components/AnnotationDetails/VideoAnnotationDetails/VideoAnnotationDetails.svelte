<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type {
        AnnotationDetailsWithPayloadView,
        AnnotationUpdateInput,
        VideoAnnotationDetailsView
    } from '$lib/api/lightly_studio_local';
    import type { Collection } from '$lib/services/types';
    import AnnotationDetails from '../AnnotationDetails.svelte';
    import VideoAnnotationSampleDetails from './VideoAnnotationSampleDetails/VideoAnnotationSampleDetails.svelte';
    import { page } from '$app/state';

    const {
        collection,
        annotationDetails,
        updateAnnotation,
        refetch
    }: {
        collection: Collection;
        annotationDetails: AnnotationDetailsWithPayloadView;
        updateAnnotation: (input: AnnotationUpdateInput) => Promise<void>;
        refetch: () => void;
    } = $props();

    const video = $derived(annotationDetails.parent_sample_data as VideoAnnotationDetailsView);
    const datasetId = $derived(page.params.dataset_id!);
</script>

{#if video.first_frame_sample_id}
    <AnnotationDetails
        {annotationDetails}
        {updateAnnotation}
        {refetch}
        collectionId={collection.collection_id!}
        collectionDatasetId={collection.dataset_id}
        parentSample={{
            width: video.width,
            height: video.height,
            url: `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${video.first_frame_sample_id}`
        }}
    >
        {#snippet parentSampleDetails()}
            <VideoAnnotationSampleDetails {datasetId} {video} />
        {/snippet}
    </AnnotationDetails>
{:else}
    <div class="flex h-full w-full items-center justify-center">
        <p>This video has no frames to show.</p>
    </div>
{/if}
