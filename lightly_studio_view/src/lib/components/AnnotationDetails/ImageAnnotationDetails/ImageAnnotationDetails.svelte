<script lang="ts">
    import { PUBLIC_SAMPLES_URL } from '$env/static/public';
    import type {
        AnnotationDetailsWithPayloadView,
        AnnotationUpdateInput,
        ImageAnnotationDetailsView
    } from '$lib/api/lightly_studio_local';
    import SampleMetadata from '$lib/components/SampleMetadata/SampleMetadata.svelte';
    import { routeHelpers } from '$lib/routes';
    import type { Dataset } from '$lib/services/types';
    import AnnotationDetails from '../AnnotationDetails.svelte';
    import AnnotationViewSampleContainer from '../AnnotationViewSampleContainer/AnnotationViewSampleContainer.svelte';

    const {
        annotationIndex,
        dataset,
        annotationDetails,
        updateAnnotation,
        refetch
    }: {
        dataset: Dataset;
        annotationDetails: AnnotationDetailsWithPayloadView;
        annotationIndex?: number;
        updateAnnotation: (input: AnnotationUpdateInput) => Promise<void>;
        refetch: () => void;
    } = $props();

    const image = $derived(annotationDetails.parent_sample_data as ImageAnnotationDetailsView);
</script>

<AnnotationDetails
    {annotationDetails}
    {updateAnnotation}
    {refetch}
    {annotationIndex}
    {dataset}
    datasetId={dataset.dataset_id!}
    parentSample={{
        width: image.width,
        height: image.height,
        url: `${PUBLIC_SAMPLES_URL}/sample/${image.sample_id}`
    }}
>
    {#snippet parentSampleDetails()}
        <AnnotationViewSampleContainer
            href={routeHelpers.toSample({
                sampleId: image.sample_id,
                datasetId: image.sample.dataset_id
            })}
        >
            <SampleMetadata sample={image} showCustomMetadata={false} />
        </AnnotationViewSampleContainer>
    {/snippet}
</AnnotationDetails>
