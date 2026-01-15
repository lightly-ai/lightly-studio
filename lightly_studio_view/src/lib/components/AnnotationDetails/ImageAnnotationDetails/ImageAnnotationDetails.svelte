<script lang="ts">
    import { PUBLIC_SAMPLES_URL } from '$env/static/public';
    import type {
        AnnotationDetailsWithPayloadView,
        AnnotationUpdateInput,
        ImageAnnotationDetailsView
    } from '$lib/api/lightly_studio_local';
    import SampleMetadata from '$lib/components/SampleMetadata/SampleMetadata.svelte';
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

    const image = $derived(annotationDetails.parent_sample_data as ImageAnnotationDetailsView);

    const datasetId = $derived(page.params.dataset_id ?? page.data?.datasetId);
    const collectionType = $derived(page.params.collection_type ?? page.data?.collectionType);
</script>

<AnnotationDetails
    {annotationDetails}
    {updateAnnotation}
    {refetch}
    {annotationIndex}
    {collection}
    collectionId={collection.collection_id!}
    parentSample={{
        width: image.width,
        height: image.height,
        url: `${PUBLIC_SAMPLES_URL}/sample/${image.sample.sample_id}`
    }}
>
    {#snippet parentSampleDetails()}
        <AnnotationViewSampleContainer
            href={datasetId && collectionType ? routeHelpers.toSample({
                datasetId,
                collectionType,
                sampleId: image.sample.sample_id,
                collectionId: image.sample.collection_id
            }) : '#'}
        >
            <SampleMetadata sample={image} showCustomMetadata={false} />
        </AnnotationViewSampleContainer>
    {/snippet}
</AnnotationDetails>
